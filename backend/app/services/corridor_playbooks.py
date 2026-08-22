"""Playbooks de corredor (SPEC-017 P4 / S17-4) — corredores como DADOS versionados.

Um playbook descreve como acionar a seguradora em um canal:
- fase URA: âncoras de menu → respostas determinísticas (sem LLM);
- dados mínimos por subserviço (slots);
- âncoras de captura (protocolo, senha, agendamento, ETA);
- gatilhos de handoff (fail-safe: passo desconhecido NUNCA responde às cegas).

FREIO (decisão do founder 2026-07-11): `finalize_anchors` detecta o passo em que a
seguradora vai CONFIRMAR/ABRIR o serviço de verdade. Ele existe SÓ para o modo
TESTE (a IA executa o fluxo inteiro e CANCELA antes de abrir — nada de acionamento
de mentira). Em modo LIVE (corredor validado) o freio não trava: o passo de
confirmação é respondido pelos próprios ura_steps e o fluxo completa ponta a ponta
sem humano. `finalize_abort_reply` = como cancelar educadamente no modo teste
(vazio = silêncio; a URA encerra por inatividade). Humano só em sinistro,
sem-corredor ou travamento real.

Seed v1: Allianz Residencial WhatsApp — minerado da conversa real da corretora
com a Allianz Assistência 24h (fluxo comprovado, valores sintéticos).
O contato real da seguradora vem da configuração da corretora/plataforma
(insurer_contact_ref), NUNCA hard-coded aqui.

DESFECHO (SPEC-063, 03/08/2026): **nem todo corredor ABRE chamado.**
`outcome`, por seguradora e por subserviço, diz como o trabalho TERMINA:

    abre        segue o fluxo até o protocolo (Azul/vidros — e todo o resto)
    encaminha   a seguradora NÃO abre chamado por este canal: ela entrega um
                FORMULÁRIO (Porto/vidros) ou uma ORIENTAÇÃO (Zurich/vidros).
                O corredor entrega isso ao segurado e encerra como
                resolvido-por-encaminhamento. Encaminhar não é falhar — é o
                desfecho correto naquela seguradora.

E onde NÃO há menu observado, o subserviço simplesmente não é declarado:
`subservice_supported()` devolve False e o caso vira handoff. 📊 Vidros só está
ligado em azul, porto e zurich porque só nessas três o rótulo do menu foi
capturado em `ura_maps` (status='observed', 03/08/2026). Inventar rótulo de menu
é o defeito que manda o segurado para a opção errada da seguradora.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple


# O `*` do NEGRITO do WhatsApp some ANTES do casamento de âncora.
#
# 📊 03/08/2026: das 426 ocorrências de âncora nos playbooks, **272 quebravam**
# se a seguradora negritasse uma palavra da frase — e negritar é o que as URAs
# fazem o tempo todo (`*Digite o CPF*`, `*1* - Guincho`). O sintoma não é erro:
# é o corredor emudecer no meio da conversa, com o cronômetro da URA correndo.
#
# O conserto pontual não fecha a classe. Havia `\*?` espalhado por 43 padrões
# (`digite o \*?cpf\*? ou \*?cnpj\*?`), e ele só defende as palavras que alguém
# lembrou de blindar: negritar `*Digite*` em vez de `*CPF*` quebra a âncora de
# novo. Tirar o `*` do TEXTO fecha as 272 e impede a 273ª — a âncora nova nasce
# protegida sem ninguém lembrar de nada.
#
# 📊 Nenhuma âncora EXIGE o asterisco: os 43 padrões usam `\*?` (opcional), que
# continua casando contra texto sem asterisco. Medido varrendo `_PLAYBOOKS` por
# `\*` não seguido de `?` → 0 ocorrências.
#
# `_` (itálico) e `~` (tachado) NÃO saem daqui, e a razão é concreta:
# `normalize_insurer_key` chama esta função e depende de `_` virar espaço para
# que `tokio_marine` case `\btokio\b`. Removê-lo fundiria a chave.
_MARCADOR_DE_NEGRITO = "*"


def _norm(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(
        ch for ch in normalized
        if not unicodedata.combining(ch) and ch != _MARCADOR_DE_NEGRITO
    ).lower()


# O PROTOCOLO É UM SÓ — E A SEGURADORA ESCREVE A ETIQUETA DELE DE SEIS JEITOS.
#
# Esta âncora nasceu dentro de `_AUTO_CAPTURE_ANCHORS` e passou a viver aqui, no
# topo, por um motivo medido:
#
# 📊 04/08/2026, `observed_events` insurer_key='allianz': **19 mensagens** trazem
# `*Protocolo N.°:*` (15) ou `*Protocolo Nrº:*` (4) — é o cabeçalho do RESUMO,
# o formato mais comum de protocolo da Allianz. A âncora do corredor RESIDENCIAL
# era própria (`protocolo\s*:?\s*\*?(\d{5,12})`) e exigia o `:` colado no
# "protocolo": `N.°:` e `Nrº:` entram no meio e ela não casa NENHUM dos 19.
# A de AUTO casa os dois — ela tolera `[^\d]{0,24}` entre a palavra e o número.
#
# Duas âncoras para o MESMO fato é o defeito: o corredor de auto captura o
# protocolo e o residencial encerra sem número, no mesmo dia, na mesma
# seguradora, no mesmo formato de mensagem. Uma definição, dois leitores.
#
# O grupo aceita dígitos com hífen: a Azul emite "protocolo ... 1-104106503215".
# HDI emite "a solicitação de GUINCHO para a assistência *9257546* foi aberta".
#
# 🔴 E FALTAVA O FORMATO MAIS COMUM DE TODOS: `*Assistência:* 9666474`.
#
# 📊 04/08/2026, `observed_events`: **30 mensagens** de HDI, Yelum e Allianz têm
# a etiqueta `Assistência:` seguida do número — é o `*Resumo da solicitação*`,
# a última mensagem do acionamento, a que fecha o caso::
#
#     *Resumo da solicitação*
#     *Placa:* AZH0926
#     *Assistência:* 9662631        <- hdi, auto
#     *Assistência:* 9666474        <- yelum, residencial (encanador)
#     Assistência: 52339760         <- allianz
#
# Nenhuma casava. As alternativas exigiam "NÚMERO DA assistência", "PARA A
# assistência" ou "SOBRE SUA assistência"; a etiqueta sozinha, com dois-pontos,
# não estava prevista. Rodando o motor de verdade sobre o resumo real, o
# resultado era `captured: {}` — o corredor abria o serviço, recebia o número na
# tela e encerrava sem ele. É assim que um acionamento fica "monitorando" para
# sempre, e é a família do defeito que deixou 50 `corridor_runs` abandonados.
#
# O `(?=\*?\s*:)` exige os DOIS-PONTOS logo depois da palavra, e é ele que
# impede o falso positivo óbvio: "Assistência 24 horas" (o nome do serviço, que
# aparece na saudação de toda sessão da família) não tem dois-pontos e continua
# não casando.
# 🔴 A ÂNCORA QUE CAPTURAVA CEP, CPF E TELEFONE COMO SE FOSSEM PROTOCOLO
#
# 📊 Medida sobre as 16.214 mensagens IN do acervo inteiro, 22/08/2026:
#
#   a alternativa `o\.?s\.?`  -> 39 mensagens capturadas, **ZERO corretas**.
#   As 39 são a sequência "os" DENTRO de palavra portuguesa comum —
#   "traç[os.]", "Sant[os] Iwamoto", "solicitaçã[o s]inistro", "serviç[os]" —
#   e o `[^\d]{0,24}` de folga então colhia o primeiro número à frente:
#     · CEP de origem/destino  ×9   (allianz, yelum, hdi, bradesco)
#     · número de SINISTRO     ×7   (porto, bradesco)
#     · um 0800                ×3   (tokio)
#     · telefone do segurado   ×4   · CPF ×1 · CNPJ de exemplo ×1 · CEP de exemplo ×1
#
# 🔴 O caso que mostra o tamanho: no bradesco o "protocolo" entregue ao segurado
#    era **o CEP do destino do guincho** — `"...areias, sao jose - sc, 88113-600"`,
#    onde o `os` casado é o de "jos[e]"... não: é o de "sao jos[e]", e o número
#    colhido é o CEP. A seguradora nem emite protocolo neste canal.
#
# E `para a assist[êe]ncia` com 24 de folga deixava caber um `é ` inteiro:
#   📊 zurich, "Seu telefone de contato para a assistência é 48984381978?"
#      -> capturava o TELEFONE. 4 vezes. Mas a mesma alternativa faz 16 capturas
#      CERTAS na hdi/yelum ("para a assistência *9070162*"), então ela não sai:
#      a folga cai de 24 para 2, que é o que `" *"` ocupa e `" é "` não.
#
# 📊 CONTROLE, o acervo inteiro, antes x depois:
#      ATUAL     368 capturas   ·   PROPOSTA  328   ·   perde 43, ganha 0
#      As 43 foram lidas uma a uma: 40 são falso positivo. As 3 que mereciam
#      ficar são da tokio (`"ordem de serviço OS7082326 - REBOQUE PESADO"`) —
#      e é por elas que entram `ordem de servi[çc]o` e `o\.?s\.?#?(?=\d)`.
#
# 🔴 A regra que sobra: `os` só é etiqueta de Ordem de Serviço quando vem
#    **colado** no número (OS1234567) ou pontuado (O.S.). Com espaço, é artigo.
#
# ⚠️ E ELA TEM DE TER **UM** GRUPO DE CAPTURA, NÃO DOIS.
#    `extract_capture_anchors` lê `m.group(1)` (linha ~3637). A primeira versão
#    desta correção pôs a folga curta numa segunda alternativa de topo — e isso
#    criava um `group(2)`. As 16 capturas certas da hdi/yelum passariam a cair
#    no grupo 2 e `group(1)` devolveria `None`: o conserto teria APAGADO os
#    acertos que ele existe para preservar. A alternância vive no SEPARADOR;
#    o número é colhido uma vez só, no fim.
_ANCORA_DE_PROTOCOLO = (
    r"(?:"
    r"(?:protocolo(?:\s+de\s+atendimento)?|ordem\s+de\s+servi[çc]o|"
    r"n[úu]mero\s+d[oa]\s+(?:sua\s+)?(?:ordem(?:\s+de\s+servi[çc]o)?|"
    r"solicita[çc][ãa]o|assist[êe]ncia|chamado)|"
    r"o\.?s\.?#?(?=\d)|"
    r"\*?assist[êe]ncia\*?(?=\*?\s*:))"
    r"[^\d]{0,24}"
    # 🔴 folga de 2, nao 24 — ver o telefone da zurich acima
    r"|(?:para a assist[êe]ncia|sobre sua assist[êe]ncia)[^\d]{0,2}"
    r")"
    r"(\d[\d-]{4,18}\d)"
)


# 🔴 O AGENDAMENTO DA PORTO NUNCA ERA CAPTURADO — P-084-8, 22/08/2026.
#
# Este **não** é artefato de máscara. Testado com texto REAL, pelo motor:
#
#   "...deve chegar ao seu endereço no dia 25/08/2026, entre 13h00 e 14h00"  -> {} 🔴
#   "...previsto para ser realizado no dia 25/08/2026, entre 14h00 e 14h30"  -> {} 🔴
#   "...previsto para ser realizado *hoje*, em até 60 minutos"   -> {eta_minutes} ✅
#
# `capture_anchors.schedule` exige a data **colada** em "para"
# (`prevista? para (?:o dia )?<data>`). A porto escreve TRÊS palavras no
# meio — "previsto para SER REALIZADO no dia X" — e o `schedule_agendado`
# da Allianz exige `Quando:` / `Agendamento para:`, que a porto não usa.
#
# 📊 Alcance medido: 5 telas residenciais (4 sessões) e 1 auto — e **todas
#    são a ÚLTIMA mensagem útil do acionamento**. Hoje o segurado recebe o
#    protocolo e NÃO SABE QUANDO O PRESTADOR VEM, que é a única coisa que
#    ele quer saber. É literalmente o defeito que o comentário de
#    `schedule_agendado` diz ter consertado na Allianz, aberto na porto.
#
# ⚠️ E `extract_capture_anchors` roda **sem DOTALL**: `[^\n]` é
#    obrigatório aqui. Um `.` casaria zero, porque estas telas têm quebra.
_ANCORA_DE_AGENDAMENTO_PORTO = (
    r"(?:previsto para ser realizado|deve chegar ao seu endere[çc]o|"
    r"agendamento\s*:)"
    r"[^\n]{0,24}?(hoje|\d{1,2}/\d{1,2}/\d{2,4})"
    r"[^\n]{0,24}?entre\s*(\d{1,2}h\d{0,2})\s*e\s*(\d{1,2}h\d{0,2})"
)


# ---------------------------------------------------------------------------
# Seed: Allianz Residencial WhatsApp v1
# ---------------------------------------------------------------------------

ALLIANZ_RESIDENCIAL_WHATSAPP_V1: Dict[str, Any] = {
    "playbook_id": "allianz-residencial-whatsapp",
    "version": 1,
    "insurer_key": "allianz",
    "line_kind": "residencial",
    "channel": "whatsapp",
    "insurer_contact_ref": "allianz_assistencia_24h",  # resolvido por config da corretora
    "description": "Assistência 24h residencial Allianz via WhatsApp (URA numerada + especialista humano).",
    # Fase URA: âncora (regex sobre a mensagem da seguradora) -> resposta.
    # {campo} = slot do caso. Ordem importa (primeiro match vence).
    "ura_steps": [
        {
            "step": "menu_tipo_seguro",
            "constante_justificada": (
                "📊 A ROTA JÁ DIZ o ramo. `menu_tipo_seguro` só existe dentro de um playbook de auto ou de residencial — a tecla não escolhe nada que o caso não tenha decidido antes de o corredor abrir."),
            "anchor": r"assist[êe]ncia 24h para qual seguro",
            "reply": "2",
            "notes": "1-Auto 2-Residência/Empresa/Condomínio 3-Vida 4-Viagem 5-Outros",
        },
        {
            "step": "menu_solicitar_para",
            "constante_justificada": (
                "📊 1-Residência 2-Veículo. O playbook é o residencial: o ramo não é uma escolha aberta aqui, é a identidade da rota."),
            "anchor": r"solicitar servi[çc]os de assist[êe]ncia para:",
            "reply": "1",
            "notes": "URA 2026: 1-Residência 2-Condomínio 3-Empresa",
        },
        {
            "step": "menu_qual_seguro",
            "constante_justificada": (
                "📊 Tela de DUAS opções: 1-Seguro Residência/Condomínio/Empresa · 2-Seguro Automotivo com serviços residenciais. Este playbook É o residencial, então 1 é a apólice certa por construção. 🔴 A tela de TRÊS opções (Residencial/Condomínio/Empresarial) é OUTRA, tem passo próprio (`menu_qual_seguro_tres_opcoes`) e ali a tecla vem do caso — foi o defeito nº 3 do BLOCO 1."),
            # 🔴 "qual O seguro QUE deseja" -> a URA de 2026 escreve "Qual
            # seguro deseja utilizar?". Duas palavras a menos, e a ancora
            # deixou de casar. 📊 A tela passou a cair no cerebro em 18/08.
            #
            # 🔴 E DUAS TELAS DIFERENTES CASAM ESTA MESMA ÂNCORA — 21/08/2026:
            #
            #   A) "...qual o seguro que deseja utilizar?
            #       *1 -* Seguro Residência, Condomínio ou Empresa
            #       *2 -* Seguro Automotivo com serviços residenciais"      "1" certo
            #
            #   B) "Qual seguro deseja utilizar?
            #       *1 - Residencial:* casa ou apartamento individual
            #       *2 - Condomínio:*  áreas comuns e estrutura
            #       *3 - Empresarial:* proteger seu negócio"                "1" ERRADO
            #
            # 📊 A rota de condomínio EXISTE e está medida: **5 sessões** passam por
            #    `Digite o *CNPJ* do titular ... exclusivamente a serviços nas áreas
            #    comuns` — e só se chega lá respondendo **2** na tela B.
            #
            # 🔴 Com "1" fixo, **todo condomínio ia para a apólice residencial** — e
            #    o chamado é recusado no local, porque o serviço não cobre unidade
            #    individual. O corredor não travava: acertava a tecla e abria o
            #    chamado errado.
            #
            # A âncora agora exige as DUAS primeiras opções da tela A. A tela B ganha
            # passo próprio, logo abaixo, com a tecla vindo do caso.
            "anchor": r"qual (?:o )?seguro (?:que )?deseja utilizar"
                      r"[\s\S]{0,80}resid[êe]ncia, condom[íi]nio ou empresa",
            "reply": "1",
            "notes": "📊 1-Residencia/Condominio/Empresa 2-Auto com servicos "
                     "residenciais. A ancora exige a 1a opcao: a tela de TRES "
                     "opcoes (Residencial/Condominio/Empresarial) e outra, e '1' "
                     "nela mandaria todo condominio para a apolice errada.",
        },
        {
            # 🔴 A TELA DE TRÊS OPÇÕES — 📊 37 sessões, e ela decide a APÓLICE.
            "step": "menu_qual_seguro_tres_opcoes",
            "anchor": r"qual seguro deseja utilizar\?[\s\S]{0,60}"
                      r"\*?1\s*-\s*resid[êe]ncial",
            "reply": "{qual_seguro_opcao}",
            "requires": ["qual_seguro_opcao"],
            "fallback_adaptive": True,
            "notes": "📊 1-Residencial (casa ou apartamento individual) "
                     "2-Condominio (areas comuns e estrutura) 3-Empresarial. "
                     "🔴 Vem do caso, NUNCA fixo: '1' num condominio abre um "
                     "chamado que sera recusado no local, porque o servico nao "
                     "cobre unidade individual. 📊 5 sessoes de condominio no acervo.",
        },
        {
            # A URA lembra o CPF do ÚLTIMO atendimento (o WhatsApp é da corretora,
            # atende N clientes) — SEMPRE re-identificar para nunca acionar na
            # apólice do cliente anterior.
            "step": "cpf_anterior",
            # 🔴 A URA de 2026 escreve "Que bom que voltou! Gostaria de
            # continuar com o CPF/CNPJ 030.###?". A frase antiga sumiu.
            # 📊 Em 18/08 so o cerebro salvou esta tela, por sorte.
            "anchor": (r"em nossa [úu]ltima conversa,? utilizamos o cpf"
                       r"|que bom que voltou.{0,80}cpf"
                       r"|continuar com o cpf"),
            "reply": "2",
            "notes": "1-Sim (continuar com o CPF anterior) 2-Não, inserir outro CPF/CNPJ",
        },
        {
            "step": "atendimento_recente",
            "anchor": r"atendimento realizado recentemente",
            "reply": "2",
            "notes": "1-Sim, mesmo atendimento 2-Não, abrir novo serviço",
        },
        {
            "step": "pedir_cpf",
            "anchor": r"digite o \*?cpf\*? ou \*?cnpj\*?",
            "reply": "{titular_cpf}",
            "requires": ["titular_cpf"],
        },
        {
            "step": "confirmar_endereco",
            "anchor": r"confirme o endere[çc]o para atendimento",
            "reply": "1",
            "notes": "Opção 1 = endereço da apólice. Divergência de endereço → handoff.",
        },
        {
            # 🔴 A ÂNCORA NUNCA CASOU. NEM UMA VEZ — 21/08/2026.
            #
            # Ela exigia "informe o número da residência". 📊 Essa frase aparece
            # **ZERO vezes** em 28.092 eventos do acervo. O que a URA escreve, e
            # escreveu de novo no acionamento validado de 19/08 às 16:36, é:
            #
            #     "Agora, me CONFIRME o número da residência."
            #     📊 180 mensagens · 72 sessões · a mais recente é a da régua
            #
            # A tela caía no cérebro toda vez. Funcionava — e custava ~14s numa
            # URA que 📊 encerra por inatividade a partir de 103s. Foi essa a
            # tela que travou o eletricista por 2min22 em 18/08.
            #
            # O verbo é opcional agora. A redação antiga continua casando: é o
            # que o CONTROLE do teste prova, e é por isso que ampliar uma
            # âncora é seguro e trocá-la não é.
            "step": "numero_residencia",
            "anchor": r"(?:informe|confirme) o n[úu]mero da resid[êe]ncia",
            "reply": "{endereco_numero}",
            "requires": ["endereco_numero"],
            "notes": "📊 'Agora, me confirme o número da residência.' — 180x, 72 sessões",
        },
        {
            "step": "confirmar_telefone",
            "anchor": r"deseja adicionar outro n[úu]mero",
            "reply": "{telefone_adicionar_opcao}",
            "requires": ["telefone_adicionar_opcao"],
            "notes": "1=Sim (informar telefone_contato) · 2=Não (usa o registrado)",
        },
        {
            "step": "informar_telefone",
            "anchor": r"informe \*?o n[úu]mero de celular completo\*? com ddd",
            "reply": "{telefone_contato}",
            "requires": ["telefone_contato"],
        },
        {
            "step": "confirmar_telefone_anotado",
            "anchor": r"anotei seu n[úu]mero",
            "reply": "1",
        },
        {
            "step": "menu_tipo_servico",
            "anchor": r"informe o tipo de\s+servi[çc]o",
            "reply": "{tipo_servico_opcao}",
            "requires": ["tipo_servico_opcao"],
            "notes": "📊 64 ocorrências: 'Vamos lá! Informe o tipo de serviço: *1 -* Serviços "
                     "Emergenciais (encanador, eletricista e chaveiro) *2 -* Para meus "
                     "eletrodomésticos *3 -* Outros serviços'",
        },
        {
            # ==============================================================
            # O CAMINHO DO ELETRODOMESTICO — SPEC-082, 18/08/2026
            # ==============================================================
            #
            # 📊 Mapeado de uma sessao REAL que terminou com protocolo
            # 51022010 (`observed_events`, sessao b2bf40e7, 28/07/2026). A
            # ordem abaixo e a ordem que a URA usou, turno a turno.
            #
            #   'Informe o tipo de servico'          -> 2  (eletrodomesticos)
            #   'Qual eletrodomestico? 1-Linha Branca' -> 1
            #   'devera ser AGENDADO. 1-Continuar'   -> 1
            #   'Escolha qual data' (7 dias uteis)   -> data
            #   'periodos manha 9-13 / tarde 13-18'  -> periodo
            #   '*Importante:* fora da garantia'     -> 1
            #   'Selecione o eletrodomestico'        -> 14 (Maquina de Lavar)
            #   'Qual problema/defeito apresentado?' -> texto
            #   'Qual a marca ?'                     -> texto
            #   'E o modelo completo?'               -> texto
            #   RESUMO                               -> 1
            #   'protocolo *51022010*'
            #
            # 🔴 A DIFERENCA QUE MUDA TUDO: eletrodomestico e AGENDADO, nao
            # e "agora". O eletricista pergunta "para quando? 1-Agora"; aqui
            # a URA escolhe DATA numa lista de sete dias uteis e depois o
            # PERIODO. Um passo que respondesse "1-Agora" aqui nao existe.
            #
            # A PRIMEIRA tela de aparelho — a CATEGORIA, nao o aparelho.
            # Ancora `qual eletrodom` para nao colidir com a segunda tela,
            # que comeca com `selecione o eletrodom`.
            "step": "menu_categoria_eletrodomestico",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": r"qual eletrodom[ée]stico precisa de conserto",
            "reply": "{eletrodomestico_categoria_opcao}",
            "requires": ["eletrodomestico_categoria_opcao"],
            "notes": "📊 14 ocorrencias. 1-Linha Branca (inclui Maquina de Lavar "
                     "e secar roupas) 2-Ar Condicionado 3-Geladeira/Freezer 4-Voltar",
        },
        {
            # "Certo! O servico de *Conserto para eletrodomestico* devera ser
            # agendado. 1-Continuar 2-Voltar"
            #
            # 📊 7 ocorrencias, e ha a variante com "(Ar condicionado)" no
            # meio — por isso a ancora nao exige o texto entre as palavras.
            "step": "confirmar_que_sera_agendado",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": r"conserto para eletrodom[ée]stico.{0,30}dever[áa] ser agendado",
            "reply": "1",
            "notes": "1-Continuar 2-Voltar. Quem pediu conserto quer continuar.",
        },
        {
            # 🔴 A DATA. 📊 6 ocorrencias:
            #   "Os agendamentos estao disponiveis de *segunda-feira* a
            #    *sexta-feira*, para os proximos *7 dias*. Escolha qual data
            #    deseja agendar: *1 -* 31/12/2025 (Quarta) ... *7 -* ..."
            #
            # As datas sao DINAMICAS — mudam a cada dia. Por isso a resposta e
            # o NUMERO da posicao, nunca a data. `1` e sempre a mais proxima.
            "step": "escolher_data_agendamento",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": r"escolha qual data deseja agendar",
            "reply": "{data_agendamento_opcao}",
            "requires": ["data_agendamento_opcao"],
            "notes": "1..7, do mais proximo ao mais distante. Somente dias uteis.",
        },
        {
            # 🔴 O PERIODO. 📊 Tres redacoes diferentes da mesma pergunta, 47
            # ocorrencias somadas — por isso a ancora e larga:
            #   "O agendamento e por periodo, a partir do proximo dia util.
            #    Manha das 09h as 13h e tarde, das 13h as 18h." (16x)
            #   "E quanto aos horarios de agendamento, sao por *periodos
            #    (manha* - das 9:00 as 13:00 ou *tarde* ...)" (14x)
            #   "O agendamento e feito em intervalo de 2 horas..." (17x)
            "step": "escolher_periodo_agendamento",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": (r"agendamento (?:[ée] por per[íi]odo|[ée] feito em intervalo)"
                       r"|hor[áa]rios de agendamento"),
            "reply": "{periodo_agendamento_opcao}",
            "requires": ["periodo_agendamento_opcao"],
            "notes": "1-manha (09-13) 2-tarde (13-18). 📊 Agendamento para o dia "
                     "seguinte e obrigatoriamente TARDE; no fim de semana, "
                     "proximo dia util a tarde.",
        },
        {
            # 🔴 O AVISO QUE PEDE RESPOSTA — e por isso NAO pode cair no
            # `avisos_informativos`, que e noop.
            #
            # 📊 "*Importante:* O servico e destinado a aparelhos/equipamentos
            # de uso domestico que estejam fora da garantia do fabricante e que
            # pertencam a residencia segurada. *Dica:* Antes d..." -> a URA
            # espera "1".
            #
            # A palavra `*Dica:*` esta na ancora do noop que eu escrevi em
            # 18/08. Este passo vem ANTES dele na lista, e por isso vence —
            # `match_ura_step` percorre em ordem. Mexer na ordem quebra isto.
            # 🔴 A PERGUNTA DE COBERTURA, E ELA VEM ANTES DO AVISO — 21/08/2026.
            #
            # 📊 A URA manda o aviso e a pergunta NA MESMA BOLHA:
            #
            #   "*Importante:* O serviço é destinado a aparelhos que estejam FORA
            #    da garantia do fabricante e que pertençam à residência segurada.
            #    (...)
            #    Qual a idade de fabricação do aparelho/equipamento?
            #    *1 -* Até 10 anos   *2 -* Mais de 10 anos de fabricação"
            #
            # 🔴 `aviso_fora_da_garantia` respondia **"1"** a essa tela. E "1" ali
            #    **não é "continuar" — é "Até 10 anos"**. O corredor AFIRMAVA a
            #    idade do aparelho sem ninguém ter perguntado.
            #
            # ⚠️ E o `regras_para_o_cliente` deste playbook já diz que o aparelho
            #    precisa ter até 10 anos. **A regra existia, e a tela que a verifica
            #    era respondida no automático.** É a coincidência de numeração — na
            #    variante sem a pergunta, "1" É "Continuar" — que escondia o defeito.
            #
            # 🔴 Por isso este passo vem ANTES: quando a pergunta está na tela, quem
            #    responde é o caso, não o corredor.
            "step": "idade_de_fabricacao",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar",
                                 "ar_condicionado"],
            "anchor": r"qual a idade de fabrica[çc][ãa]o do aparelho",
            "reply": "{idade_aparelho_opcao}",
            "requires": ["idade_aparelho_opcao"],
            "fallback_adaptive": True,
            "notes": "📊 2 telas, 3 sessoes. 1-Ate 10 anos 2-Mais de 10 anos. "
                     "🔴 E pergunta de COBERTURA: '2' e recusa. Responder '1' fixo "
                     "abre um chamado que sera negado quando o tecnico chegar.",
        },
        # ==================================================================
        # 🔴 O OITAVO DEFEITO DA MESMA FAMÍLIA — 22/08/2026
        # ==================================================================
        #
        # Achado pelo COMPARADOR CONSERTADO (P-084-14), na primeira vez que ele
        # rodou. Eu tinha consertado sete no BLOCO 1 e **perdido este**, porque
        # a régua antiga contava casamento e ele casava.
        #
        # 📊 A âncora `fora da garantia do fabricante` casa DUAS telas, e eu
        #    supus uma terceira que **não existe no corpus**:
        #
        #   A) "...fora da garantia... Você precisa de:
        #       *1 -* Conserto do ar condicionado
        #       *2 -* Limpeza do ar condicionado"          <- o galho do AR
        #
        #   B) "...fora da garantia... Qual a idade de fabricação?
        #       *1 -* Até 10 anos  *2 -* Mais de 10 anos"  <- `idade_de_fabricacao`
        #
        #   C) "...fora da garantia... *1 -* Continuar"     <- 🔴 EU INVENTEI. 0 telas.
        #
        # 🔴 Ou seja: `reply: "1"` estava errado em **100% das telas que o passo
        #    casava**. Num caso de MÁQUINA DE LAVAR, o corredor digitava
        #    "Conserto do ar condicionado" — e abria um serviço inteiramente outro.
        #
        # ⚠️ E a lição sobre a lição: no BLOCO 1 escrevi na `notes` que "aqui '1'
        #    é Continuar". **Escrevi uma variante que eu não tinha medido.** O
        #    comentário parecia evidência e era suposição — o defeito que a §12.1
        #    do CLAUDE.md nomeia, cometido dentro do conserto dele mesmo.
        {
            "step": "ar_condicionado_servico",
            "only_subservices": ["ar_condicionado"],
            "anchor": (r"fora da garantia do fabricante[\s\S]{0,120}"
                       r"conserto do ar condicionado"),
            "reply": "{ar_condicionado_servico_opcao}",
            "requires": ["ar_condicionado_servico_opcao"],
            "fallback_adaptive": True,
            "notes": "📊 1 tela. 1-Conserto do ar condicionado 2-Limpeza do ar "
                     "condicionado. 🔴 São TRABALHOS DIFERENTES: conserto é defeito, "
                     "limpeza é manutenção — e a limpeza costuma nem ser coberta. "
                     "Vem do relato, nunca fixo. "
                     "⚠️ `only_subservices` fecha a porta que estava aberta: um caso "
                     "de máquina de lavar não tem o que fazer nesta tela.",
        },
        {
            # 🔴 O APARELHO. Maquina de Lavar roupas = 14.
            #
            # 📊 "Selecione o eletrodomestico que precisa de conserto ?
            #  1-Geladeira 2-Freezer 3-Frigobar 4-Adega 5-Micro-ondas 6-Fogao
            #  7-Forno 8-Cooktop 9-Filtro/Purificador 10-Lavadora de loucas
            #  11-Coifa/depurador 12-Exaustor 13-Secadora de roupas
            #  14-Maquina de Lavar roupas  15-Outros"
            #
            # 🔴 ATENCAO A DIFERENCA: 10 e lavadora de LOUCAS, 13 e SECADORA,
            # 14 e maquina de lavar ROUPAS. Tecla errada abre chamado para o
            # aparelho errado, e o tecnico chega para consertar outra coisa.
            "step": "menu_aparelho",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": r"selecione o eletrodom[ée]stico que precisa de conserto",
            "reply": "{eletrodomestico_opcao}",
            "requires": ["eletrodomestico_opcao"],
            "notes": "10=lava-loucas 13=secadora 14=MAQUINA DE LAVAR ROUPAS 15=outros",
        },
        {
            # "Para finalizar a abertura do atendimento, vamos precisar de mais
            #  algumas informacoes. Qual problema/defeito apresentado?"
            #
            # 📊 Resposta real da sessao 51022010: "Lava mais nao joga a agua
            # fora". Texto livre, do proprio segurado.
            "step": "problema_do_aparelho",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": r"qual problema/?defeito apresentado",
            "reply": "{problema_descricao}",
            "notes": "texto livre; a atendente ja coleta este slot",
        },
        {
            "step": "aparelho_marca",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": r"^\s*qual a marca\s*\??\s*$|qual a marca do (?:aparelho|equipamento)",
            "reply": "{aparelho_marca}",
            "requires": ["aparelho_marca"],
            "notes": "📊 6 ocorrencias, pergunta seca: 'Qual a marca ?'",
        },
        {
            "step": "aparelho_modelo",
            "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
            "anchor": r"e o modelo completo|qual o modelo",
            "reply": "{aparelho_modelo}",
            "requires": ["aparelho_modelo"],
            "notes": "📊 4 ocorrencias: 'E o modelo completo?'. Resposta real: "
                     "'Turbo capacidade 15kg' — nao precisa ser exato.",
        },
        {
            # 🔴 O SEGUNDO MENU — o que escolhe o PROFISSIONAL de verdade.
            #
            # 📊 04/08/2026, `observed_events` insurer_key='allianz': 13
            # ocorrências de "De qual profissional? / *1 -* Eletricista /
            # *2 -* Encanador / *3 -* Desentupimento / *4 -* Chaveiro /
            # *5 -* Voltar" — e `match_ura_step` devolvia NENHUM passo.
            #
            # O playbook conhecia só a URA anterior (`informe o tipo de
            # serviço`), que escolhe a FAMÍLIA ("1 - Serviços Emergenciais").
            # Quem escolhe o ofício é esta tela, e ela vem logo depois.
            #
            # 📊 Fluxo real completo (sessão 9694992d, 13/07/2026, encanador):
            #   'Informe o tipo de serviço' → 1
            #   'De qual profissional?'     → 2
            #   'E para quando precisa do *Encanador*?' → 1 (Agora)
            #   ... árvore do problema ... → RESUMO → 1 → protocolo 52652744
            #
            # Sem este passo o menu caía no cérebro adaptativo, que teria de
            # adivinhar a tecla do ofício — e a tecla errada não falha: ela
            # abre chamado de OUTRO profissional na apólice do segurado.
            "step": "menu_profissional",
            "anchor": r"de qual profissional",
            "reply": "{profissional_opcao}",
            "requires": ["profissional_opcao"],
            "notes": "📊 13 ocorrências: 1-Eletricista 2-Encanador 3-Desentupimento 4-Chaveiro 5-Voltar",
        },
        {
            # 🔴 O PASSO QUE FALTAVA — acrescentado em 18/08/2026.
            #
            # 📊 Medido no acervo: a URA residencial manda esta tela DEZ vezes
            # nas 24 sessões Allianz reais --
            #
            #     "E para quando precisa do *Encanador*?
            #      *1 -* Agora  *2 -* Quero agendar  *3 -* Voltar"
            #
            # O passo existia SÓ no playbook de automóvel, e a âncora de lá
            # (reboque|guincho|serviço|profissional) nao casa "*Eletricista*"
            # nem "*Encanador*" — sao os nomes que a URA usa no residencial.
            #
            # Sem este passo a tela caia no cerebro adaptativo, que em modo
            # TESTE recebe a regra "se a seguradora for CONFIRMAR/ABRIR o
            # servico (agendar, ...), responda NAO_SEI". Ele lia a palavra
            # "agendar" na propria tela e travava. Duas recusas e a sessao ia
            # para `needs_human`.
            #
            # Ou seja: o teste falhava POR SER TESTE, num passo que em modo
            # real passaria. A ancora agora aceita qualquer profissional.
            "step": "quando",
            "constante_justificada": (
                "📊 'Agora' x 'Agendar'. O corredor só é acionado quando a corretora abriu um caso de assistência — que é, por definição, agora. ⚠️ Se um dia existir rota de AGENDAMENTO, esta constante vira slot."),
            "anchor": r"para quando precisa (?:do|da)\s*\*?(?:eletricista|encanador|chaveiro|"
                      r"desentupimento|desentupidor|profissional|servi[çc]o|t[ée]cnico)",
            "reply": "1",
            "notes": "1-Agora 2-Quero agendar 3-Voltar. Urgencia e o default do "
                     "corredor: quem escreve para a corretora quer agora.",
        },
        {
            # 🔴 A TELA QUE TRAVOU O TESTE DE 18/08/2026.
            #
            # Texto real, do banco (`observed_events`, 01:51:33 e 01:59:07):
            #
            #   *Importante:* Esse servico de eletricista esta disponivel
            #   apenas para reparos eletricos na residencia
            #   *1 -* Preciso de reparo eletrico para residencia
            #   *2 -* Preciso de reparos eletricos em aparelhos ou
            #         eletrodomesticos.
            #
            # 📊 O Atlas ja tinha VISTO esta tela OITO VEZES desde 28/07. Ela
            # nunca virou passo, porque a ponte entre "o Atlas sabe" e "o
            # corredor sabe" so existe para drift cosmetico -- tela nova de
            # menu e classificada `structural` e vai para alerta, nao para o
            # Alfaiate. `playbook_overlays` tem ZERO linhas, em todas as
            # corretoras.
            #
            # Sem passo, a tela ia ao cerebro, que respondeu 459 tokens de
            # prosa numa tela de dois botoes -- reprovado por uma regua de 400
            # caracteres que o prompt nunca lhe contou. A Allianz esperou 248
            # segundos e encerrou por inatividade.
            #
            # A corretora aciona para a CASA do segurado. Eletrodomestico e
            # outro servico, e a propria tela avisa que nao esta disponivel.
            "step": "tipo_de_reparo_eletrico",
            "constante_justificada": (
                "📊 'Preciso de reparo elétrico para residência' x as outras. O playbook é o residencial."),
            "anchor": r"apenas para reparos el[ée]tricos|reparo el[ée]trico para resid[êe]ncia",
            "reply": "1",
            "notes": "1-reparo na residencia 2-aparelhos/eletrodomesticos. "
                     "📊 8 ocorrencias no acervo desde 28/07/2026.",
        },
        {
            # A tela seguinte, também medida no acervo. Vem logo depois do
            # `tipo_de_reparo_eletrico` e também não existia.
            #
            #   O que aconteceu?
            #   *1 -* Casa inteira ou parcial sem energia
            #   *2 -* Curto circuito ...
            #
            # 🔴 SEM `reply` FIXO. Esta escolhe o TIPO DE DEFEITO: tecla errada
            # abre chamado errado. Vai como slot, preenchido do caso — igual a
            # `profissional_opcao`. Uma constante aqui seria pior que o
            # silencio que ela conserta.
            # 🔴 A MESMA PERGUNTA, TRÊS OFÍCIOS, TRÊS LISTAS DE OPÇÕES — 21/08/2026.
            #
            # A âncora era `o que aconteceu\?`, seca. 📊 Rodado no motor, o efeito
            # real era este:
            #
            #   tela do ENCANADOR  x subservice=encanador   -> None
            #                      x subservice=eletricista -> o_que_aconteceu, "{problema_eletrico_opcao}"
            #   tela do CHAVEIRO   x subservice=chaveiro    -> None
            #                      x subservice=eletricista -> o_que_aconteceu, "{problema_eletrico_opcao}"
            #
            # **As duas metades são defeito.** Num caso de eletricista o corredor
            # digitava a tecla do vazamento; num caso de encanador ou chaveiro ele
            # emudecia. A URA escreve a mesma frase e muda as opções embaixo.
            #
            # 🔴 A âncora agora exige a PRIMEIRA OPÇÃO, não só a pergunta. É o que
            #    separa as três — e é o mesmo princípio do `PADRAO_DE_CARDAPIO`:
            #    o que distingue não está na pergunta, está na lista.
            "step": "o_que_aconteceu",
            "only_subservices": ["eletricista"],
            "anchor": r"o que aconteceu\?[\s\S]{0,60}casa inteira ou parcial sem energia",
            "reply": "{problema_eletrico_opcao}",
            "requires": ["problema_eletrico_opcao"],
            "notes": "📊 1-Casa inteira/parcial sem energia 2-Curto circuito 3-outros. "
                     "Vem do caso, nunca fixo. A ancora exige a 1a opcao porque o "
                     "encanador e o chaveiro usam a MESMA pergunta.",
        },
        {
            # 🔴 MESMA PERGUNTA, OUTRO OFÍCIO — 📊 2 redações, 4 sessões.
            #    "1-Vazamento em dispositivo (sifões, rabichos, torneiras, válvulas)
            #     2-Vazamento em tubulação de água ou esgoto"
            "step": "o_que_aconteceu_encanador",
            "only_subservices": ["encanador"],
            "anchor": r"o que aconteceu\?[\s\S]{0,60}vazamento em",
            "reply": "{problema_vazamento_opcao}",
            "requires": ["problema_vazamento_opcao"],
            "fallback_adaptive": True,
            "notes": "📊 4 sessoes. 1-Vazamento em dispositivo 2-Vazamento em tubulacao. "
                     "A resposta muda a arvore inteira que vem depois.",
        },
        {
            # 🔴 MESMA PERGUNTA, TERCEIRO OFÍCIO — 📊 2 sessões, e uma delas MORREU
            #    aqui: `aa2e0a68`, 03/07/2026, "Opção inválida" -> "Vamos tentar
            #    novamente" -> transferência ao especialista. Sem protocolo.
            "step": "o_que_aconteceu_chaveiro",
            "only_subservices": ["chaveiro"],
            "anchor": r"o que aconteceu\?[\s\S]{0,80}"
                      r"(?:perda ou quebra das chaves|roubo ou furto das chaves)",
            "reply": "{problema_chave_opcao}",
            "requires": ["problema_chave_opcao"],
            "fallback_adaptive": True,
            "notes": "📊 2 sessoes. 1-Perda ou quebra das chaves 2-Roubo ou furto "
                     "3-Arrombamento, roubo ou furto da residencia.",
        },
        {
            # "E para finalizar: descreva detalhadamente o que aconteceu"
            "step": "descricao_detalhada",
            "anchor": r"descreva detalhadamente",
            "reply": "{problema_descricao}",
            "notes": "texto livre; o slot ja e coletado pela atendente",
        },
        {
            "step": "complemento_referencia",
            "anchor": r"informe o complemento do endere[çc]o",
            "reply": "{ponto_referencia}",
            "notes": "URA 2026 pede complemento/referência (texto livre); 'não' aceito",
        },
        {
            # Confirmação FINAL (RESUMO → 'Podemos confirmar o atendimento?').
            # Só é alcançada em modo LIVE — em modo teste o freio cancela antes.
            "step": "confirmar_atendimento",
            "anchor": r"podemos confirmar o atendimento",
            "reply": "1",
            "notes": "1-Sim 2-Não, reiniciar 3/0-Sair",
        },
        {
            # 🔴 TELAS QUE NAO PEDEM NADA — acrescentado em 18/08/2026.
            #
            # O playbook de AUTO ja tinha este passo, com o motivo escrito:
            # "o adaptativo respondia 'Ciente, pode prosseguir' e quebrava o
            # menu". O residencial nao tinha, e leva as MESMAS telas.
            #
            # 📊 Medido no acervo das 24 sessoes Allianz residenciais:
            #     Termo de Privacidade ................. 31x
            #     "Tenho algumas dicas importantes" .... 15x
            #     "a Allianz oferece diversos tipos" ... 19x
            #     "Opcao invalida." ....................  6x
            #     "Vamos tentar novamente." ............  6x
            #
            # Nenhuma pede resposta. Responder qualquer coisa nelas empurra o
            # menu para um estado que o corredor nao sabe ler.
            #
            # Fica DEPOIS da confirmacao final de proposito: `match_ura_step`
            # percorre na ordem, e uma ancora larga como esta antes dela
            # poderia engolir a tela que importa.
            "step": "avisos_informativos",
            "anchor": (r"termo de privacidade|dicas importantes para conseguir te atender|"
                       r"fique tranquilo, vamos te ajudar|vale lembrar:|voc[êe] sabia\?|"
                       r"op[çc][ãa]o inv[áa]lida|vamos tentar novamente|"
                       r"oferece diversos tipos de seguro|disjuntor est[áa] na posi[çc][ãa]o|"
                       # 🔴 `\*dica:\*` SAIU EM 21/08/2026 — âncora morta.
                       #
                       # `match_ura_step` normaliza o texto com `_norm`, que
                       # **remove os asteriscos** antes de comparar. Uma
                       # alternativa que EXIGE `*` literal nunca casa — nem uma
                       # vez, em nenhuma tela, desde que entrou (commit 8aa15be,
                       # 17/08).
                       #
                       # Era inócua na prática, porque `aviso_fora_da_garantia`
                       # pega aquela tela antes. Mas deixava o guarda
                       # `test_o_negrito_da_seguradora_nao_emudece_o_corredor`
                       # VERMELHO em produção — e guarda vermelho que todo mundo
                       # aprende a ignorar é pior que guarda nenhum.
                       #
                       # A palavra "dica" já é coberta por `dicas importantes
                       # para conseguir te atender`, logo acima.
                       r"precisando estamos por aqui|agradece o seu contato"),
            "reply": "",
            "noop": True,
            "notes": "mensagens informativas/erro da URA — NUNCA responder",
        },
    ],
    # Subserviços -> slots mínimos (do caso) antes de iniciar o acionamento.
    #
    # DOIS menus, duas opções. `tipo_servico_opcao` responde "Informe o tipo de
    # serviço" (a FAMÍLIA); `profissional_opcao` responde "De qual profissional?"
    # (o OFÍCIO). Quem injeta os dois nos slots é `new_dispatch_session`, pela
    # regra do sufixo `_opcao` — a mesma que já impede que eles sejam cobrados
    # do segurado em `missing_slots_for_subservice`.
    "subservices": {
        "eletricista": {
            "tipo_servico_opcao": "1",
            "profissional_opcao": "1",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao", "periodo_preferido", "risco_confirmado_sem_fumaca",
                               "qual_seguro_opcao"],
        },
        # ==================================================================
        # MAQUINA DE LAVAR ROUPAS — SPEC-082, 18/08/2026
        # ==================================================================
        #
        # 🔴 OUTRO GALHO DA URA, nao uma variacao do eletricista.
        #
        #   eletricista        tipo_servico_opcao = "1"  (Emergenciais)
        #   maquina de lavar   tipo_servico_opcao = "2"  (Eletrodomesticos)
        #
        # E o desfecho e diferente: emergencial e "agora"; eletrodomestico e
        # AGENDADO, com data escolhida numa lista de sete dias uteis.
        #
        # 📊 As regras que a propria URA declara, e que a atendente precisa
        # dizer ao segurado ANTES de acionar:
        #   · aparelho com ate 10 anos de idade
        #   · FORA da garantia do fabricante
        #   · 2 utilizacoes por vigencia (Linha Branca e Ar-Condicionado
        #     contam separado, 1 evento cada)
        #   · o tecnico PODE levar o aparelho para a base
        #   · mao de obra coberta; PECAS sao do cliente
        #   · reembolso de prestador proprio: R$ 150 por evento, R$ 300 por
        #     vigencia
        "maquina_de_lavar": {
            "tipo_servico_opcao": "2",
            "eletrodomestico_categoria_opcao": "1",
            "eletrodomestico_opcao": "14",
            "required_slots": [
                "titular_cpf", "endereco_numero", "telefone_contato",
                "problema_descricao", "aparelho_marca", "aparelho_modelo",
                "periodo_preferido",
                # 🔴 A IDADE DO APARELHO É PERGUNTA DE COBERTURA, E ELA VEM DO
                #    CLIENTE — nunca de derivação e nunca de constante.
                #    📊 A URA pergunta "Qual a idade de fabricação do aparelho?
                #    1-Até 10 anos 2-Mais de 10 anos", e `2` é RECUSA. A regra
                #    logo acima já diz "aparelho com até 10 anos"; o que faltava
                #    era o corredor PERGUNTAR em vez de afirmar.
                #    ⚠️ Nenhuma palavra do relato do segurado diz a idade de
                #    fabricação. Derivar aqui seria inventar o fato que decide
                #    a cobertura — por isso ele é coletado, não traduzido.
                "idade_aparelho_opcao",
            ],
        },
        "chaveiro": {
            "tipo_servico_opcao": "1",
            "profissional_opcao": "4",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao", "periodo_preferido",
                               "qual_seguro_opcao"],
        },
        # ENCANADOR (SPEC-063, 03/08/2026): mesma espinha do eletricista — mesma
        # opção de URA ("1 - casa"), mesmos dados de apólice/contato — e os slots
        # do problema trocados para VAZAMENTO. O eletricista pergunta se há
        # fumaça; o encanador pergunta se a água está escorrendo e se o registro
        # foi fechado. É o mesmo padrão de guardrail: a pergunta que separa
        # "pinga a torneira" de "está alagando" tem de ser feita ANTES do
        # acionamento, porque as duas frases pedem prioridades diferentes.
        # 💭 A URA da Allianz não pede estes campos — quem os usa é o
        # ESPECIALISTA humano da assistência (e a corretora, para priorizar).
        "encanador": {
            "tipo_servico_opcao": "1",
            "profissional_opcao": "2",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao",
                               "periodo_preferido", "vazamento_local", "agua_escorrendo",
                               "risco_confirmado_registro_fechado"],
        },
        # DESENTUPIMENTO — a opção 3 do menu real, que não era serviço declarado.
        #
        # 📊 04/08/2026: "De qual profissional? ... *3 -* Desentupimento" aparece
        # nas 13 ocorrências do menu. Sem estar em `subservices`,
        # `subservice_supported()` devolvia False, `missing_slots_for_subservice`
        # devolvia `[SUBSERVICO_INVALIDO]` e o caso virava handoff — na
        # seguradora RESIDENCIAL mais observada do acervo, com a tecla à vista.
        #
        # A HDI residencial já o declara desde 03/08. Um mesmo trabalho existir
        # num corredor e não no outro não é escopo: é esquecimento.
        #
        # Os slots do problema são os do ENCANADOR menos o registro fechado: quem
        # está com o ralo entupido não tem registro para fechar. É a mesma
        # decisão que separa "pinga a torneira" de "está alagando", aplicada ao
        # trabalho certo.
        "desentupimento": {
            "tipo_servico_opcao": "1",
            "profissional_opcao": "3",
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao",
                               "periodo_preferido"],
        },
        "eletrodomesticos": {
            # Sem `profissional_opcao`: eletrodoméstico sai pela opção 2 do PRIMEIRO
            # menu ("Para meus eletrodomésticos") e a tela "De qual profissional?"
            # não aparece nesse ramo. Declarar uma tecla que a URA não mostra é o
            # defeito que manda o segurado para a opção errada.
            "tipo_servico_opcao": "2",
            # 🔴 AS DUAS TECLAS QUE FALTAVAM — SPEC-082, 18/08/2026.
            #
            # Este subserviço existia com UMA tecla só, e travaria em DOIS
            # menus que a URA mostra logo depois: "Qual eletrodoméstico?"
            # (categoria) e "Selecione o eletrodoméstico" (o aparelho).
            #
            # 📊 É o mesmo defeito que travou o teste do eletricista em
            # 18/08: um passo que exige um slot que ninguém preenche fica
            # em silêncio, e alguém tem de clicar do celular.
            #
            # `1` é Linha Branca — a categoria que contém máquina de lavar,
            # fogão, micro-ondas, lava-louças. `15` é "Outros": o genérico
            # não sabe QUAL aparelho é, e "Outros" é a única tecla honesta.
            # Quem sabe o aparelho usa um subserviço específico, como
            # `maquina_de_lavar`.
            "eletrodomestico_categoria_opcao": "1",
            "eletrodomestico_opcao": "15",
            # 📊 A URA pergunta marca e modelo em telas SEPARADAS ("Qual a
            # marca ?" e depois "E o modelo completo?"). Um slot só, com os
            # dois juntos, responderia a primeira tela com o texto da segunda.
            "required_slots": ["titular_cpf", "endereco_numero", "telefone_contato",
                               "aparelho_marca", "aparelho_modelo",
                               "problema_descricao", "periodo_preferido"],
        },
    },
    # Fase humana da seguradora: orientação para a LLM (guardada) responder.
    "human_phase_guidance": (
        "Você fala com o especialista da assistência em nome da corretora. "
        "Apresente-se como a corretora, confirme titular/CPF quando pedido, descreva o problema com os dados do caso, "
        "responda agendamento com o período preferido do cliente (manhã 9-13 / tarde 13-18, a partir do próximo dia útil). "
        "Use SOMENTE dados do caso. Nunca invente. Se pedirem algo que não está no caso, registre pendência e pare."
    ),
    # FREIO (modo teste): a URA residencial 2026 completa TUDO sozinha até o
    # protocolo — sem estas âncoras a LLM confirmaria um serviço real no teste.
    "finalize_anchors": [
        r"podemos confirmar o atendimento", r"posso confirmar", r"deseja confirmar",
        # 🔴 O FURO DO FREIO — 21/08/2026.
        #
        # `allianz-auto` tem esta âncora desde sempre (`_ALLIANZ_FAMILY_FINALIZE`).
        # O residencial não tinha. E a tela existe, com este texto exato:
        #
        #   "Antes de prosseguirmos, poderia me confirmar se os DADOS A SEGUIR
        #    ESTÃO CORRETOS, por gentileza?"
        #   📊 154 mensagens · 64 sessões
        #
        # São 64 sessões que passaram pela conferência **sem freio nenhum**. E o
        # freio não é só o "cancela no teste": é ele que arma
        # `_conferir_antes_de_confirmar`, a última porta antes de mandar um
        # prestador ao endereço errado.
        #
        # Duas seguradoras da MESMA família com listas diferentes é o defeito
        # que ninguém vê, porque cada uma parece completa sozinha.
        r"dados a seguir est[ãa]o corretos",
    ],
    "finalize_abort_reply": "SAIR",  # a URA aceita SAIR a qualquer momento
    # Âncoras de captura no retorno da seguradora (formatos 2024 E 2026).
    # `protocol` é a definição ÚNICA do arquivo (ver `_ANCORA_DE_PROTOCOLO`): a
    # âncora própria que morava aqui perdia os 19 `*Protocolo N.°:*` do RESUMO.
    # `password` e `schedule` continuam próprios — a senha de acesso de 4 dígitos
    # e o "entre 9h e 13h" são da assistência residencial e de mais ninguém.
    "capture_anchors": {
        "protocol": _ANCORA_DE_PROTOCOLO,
        "password": r"senha (?:de acesso|ser[áa]).*?(\d{4})",
        "schedule": r"agendad[ao] para o dia\s*(\d{1,2}(?:/\d{1,2}(?:/\d{2,4})?)?)\s*,?\s*entre\s*(\d{1,2}\s?h)\s*e\s*(\d{1,2}\s?h)",
        # 🔴 O AGENDAMENTO DO ELETRODOMESTICO — SPEC-082, 18/08/2026.
        #
        # A ancora acima espera "agendado para o dia X, entre Yh e Zh". 📊 O
        # fluxo de eletrodomestico NUNCA diz isso: a data e escolhida num menu
        # de sete dias uteis, muito antes, e o desfecho so traz o protocolo.
        #
        # Sem esta segunda ancora o segurado receberia o numero do chamado e
        # NAO SABERIA QUANDO O TECNICO VEM — que e a unica coisa que ele
        # realmente quer saber.
        #
        # 📊 A fonte certa e o RESUMO, porque e o que a propria seguradora
        # confirma antes de abrir. Duas redacoes medidas, na mesma sessao:
        #
        #   *Quando:* Quarta-feira, 31/12/2025
        #   *Periodo:* manha das 09:00 as 13:00
        #
        #   *Agendamento para:* Terca-feira, 06/01/2026
        #   *Periodo:* 13:00 as 18:00 (tarde)
        # 🔴 AMPLIADA EM 21/08/2026 — ela cobria UMA das três redações reais,
        # e justamente não a do acionamento validado.
        #
        # A versão anterior exigia `periodo:` COM dois-pontos e dois espaços no
        # fim. 📊 A tela que apareceu em 19/08 às 16:39, um minuto antes do
        # protocolo da Clarissa, escreve assim:
        #
        #   "Agendamento para: *Quinta-feira 20/08/2026*, *período da tarde
        #    das 13:00 às 18:00* Podemos continuar ?"
        #
        # Sem dois-pontos depois de "período", e terminando em "Podemos". A
        # âncora não casou, o `schedule` não foi capturado, e a mensagem que
        # saiu ao cliente foi "Prontinho! ✅ Sua assistência foi aberta" — sem
        # data e sem período.
        #
        # As três redações medidas no acervo, todas cobertas agora:
        #   "agendamento para: quinta-feira 20/08/2026, periodo da tarde das…"
        #   "agendamento para: terca-feira 03/03/2026, periodo da tarde das…"
        #   "quando: quarta-feira, 31/12/2025  periodo: manha das 09:00 as…"
        #
        # O fim é `podemos` OU dois espaços OU fim de texto — porque a URA às
        # vezes emenda a pergunta na mesma bolha e às vezes não.
        "schedule_agendado": (
            r"(?:quando|agendamento para):\s*(.{0,45}?)\s*,?\s*"
            r"(?:per[ií]odo)(?::)?\s*(?:d[ao]\s*)?(.{3,50}?)\s*"
            r"(?:podemos|\s{2,}|$)"),
    },
    # Resumo estruturado ao ESPECIALISTA humano (fluxo real 01/04/2026: a URA
    # transfere emergenciais ao analista — a operadora abre com o caso mastigado).
    "opening_template": (
        "Ola, aqui e a corretora. Preciso acionar {subservice_label} para a residencia do nosso segurado.\n"
        "Titular: {titular_nome} (CPF {titular_cpf})\n"
        "Endereco: o da apolice, numero {endereco_numero}\n"
        "Problema: {problema_descricao}\n"
        "Telefone de contato: {telefone_contato}\n"
        "Periodo preferido: {periodo_preferido}"
    ),
    "subservice_labels": {
        "eletricista": "eletricista", "chaveiro": "chaveiro",
        "encanador": "encanador", "desentupimento": "desentupimento",
        "eletrodomesticos": "reparo de eletrodomestico",
        "maquina_de_lavar": "conserto da maquina de lavar",
    },
    # Regras fixas a repassar ao cliente junto do agendamento.
    "client_instructions": [
        "É necessário haver um maior de 18 anos no local para receber o prestador.",
        "O prestador vai pedir uma senha de acesso: são os 4 últimos números do telefone informado.",
    ],
    # ======================================================================
    # AS REGRAS DE COBERTURA QUE A PRÓPRIA URA DECLARA — 19/08/2026
    # ======================================================================
    #
    # 🔴 Elas existiam só em COMENTÁRIO de código, dentro do subserviço
    # `maquina_de_lavar`. Comentário não chega a lugar nenhum: nem ao prompt
    # do atendente, nem ao cliente. O resultado prático é a atendente abrir um
    # chamado para um aparelho de doze anos sem avisar ninguém, e a recusa
    # acontecer com o técnico já na porta.
    #
    # 📊 Cada linha é texto lido nas telas reais da URA da Allianz, na sessão
    # que terminou com o protocolo 51022010 (28/07/2026). Nada aqui é
    # inferência.
    #
    # Ficam por subserviço porque não valem para todos: um eletricista
    # emergencial não tem regra de idade de aparelho.
    # 🔴 NOME PRÓPRIO, e não `coverage_guardrails` — 19/08/2026.
    #
    # `coverage_guardrails` JÁ EXISTE em três corredores (hdi, porto, yelum
    # residenciais) e ali é uma LISTA de observações internas, marcadas 📊,
    # escritas para quem MANTÉM o corredor. Reaproveitar o nome com outro
    # formato criaria duas coisas com um nome só — e o leitor teria de
    # adivinhar qual delas está lendo (CLAUDE.md §6: um termo, uma definição).
    #
    # Este campo é outra coisa: texto que a ATENDENTE fala com o CLIENTE,
    # recortado por subserviço. Nome diferente porque significado diferente.
    "regras_para_o_cliente": {
        "eletrodomesticos": [
            "O aparelho precisa ter até 10 anos de fabricação.",
            "Precisa estar FORA da garantia do fabricante e pertencer à residência segurada.",
            "A mão de obra é coberta; as PEÇAS são por conta do cliente.",
            "São 2 utilizações por vigência (Linha Branca e Ar-Condicionado contam separado).",
            "O técnico pode precisar levar o aparelho para a base dele.",
        ],
        "maquina_de_lavar": [
            "O aparelho precisa ter até 10 anos de fabricação.",
            "Precisa estar FORA da garantia do fabricante e pertencer à residência segurada.",
            "A mão de obra é coberta; as PEÇAS são por conta do cliente.",
            "São 2 utilizações por vigência (Linha Branca e Ar-Condicionado contam separado).",
            "O técnico pode precisar levar o aparelho para a base dele.",
        ],
    },
    # 🔴 O QUE MUDA NO DESFECHO, por subserviço. O atendente precisa dizer
    # isto ANTES, porque muda a expectativa do cliente na hora.
    #
    # 📊 Emergencial é "agora"; eletrodoméstico é AGENDADO — a URA escolhe uma
    # data numa lista de sete dias úteis e depois o período. Um cliente que
    # ouviu "vou acionar" e esperava alguém em uma hora liga de volta bravo.
    "expectativa_do_desfecho": {
        "eletricista": "atendimento emergencial: o prestador vai HOJE, sem agendamento.",
        "encanador": "atendimento emergencial: o prestador vai HOJE, sem agendamento.",
        "chaveiro": "atendimento emergencial: o prestador vai HOJE, sem agendamento.",
        "desentupimento": "atendimento emergencial: o prestador vai HOJE, sem agendamento.",
        "eletrodomesticos": ("conserto AGENDADO: escolhe-se uma data entre os próximos "
                             "7 dias úteis e um período (manhã 9h-13h ou tarde 13h-18h). "
                             "Não é hoje."),
        "maquina_de_lavar": ("conserto AGENDADO: escolhe-se uma data entre os próximos "
                             "7 dias úteis e um período (manhã 9h-13h ou tarde 13h-18h). "
                             "Não é hoje."),
    },
    # Fail-safe.
    "handoff_triggers": [r"sinistro", r"n[ãa]o localizamos", r"cpf.*inv[áa]lido", r"n[ãa]o foi poss[íi]vel"],
    "unknown_step_policy": "pause_and_handoff",  # nunca responder às cegas
}

# ===========================================================================
# SPEC-031: Assistência AUTO no WhatsApp (multi-seguradora)
# Playbooks minerados das conversas REAIS da AutoFleet com as seguradoras
# (guincho/bateria/pneu/chaveiro). Vidro NÃO entra aqui — vai pelo portal.
#
# Diferença estrutural vs. residencial:
# - A URA de auto transfere cedo para atendente e coleta LOCAL (texto livre) →
#   o grosso é conduzido pelo cérebro adaptativo guardado (human_phase), que já
#   existe. O playbook fixa só os menus estáveis + o FREIO de finalização.
# - `opening_template`: resumo estruturado do pedido (como a operadora real
#   colava ao cair no atendente humano da seguradora).
# - `finalize_anchors`: FREIO — quando a URA vai CONFIRMAR/ABRIR o serviço de
#   fato, o motor pausa (needs_human) em vez de confirmar sozinho. Conservador
#   de propósito: frear cedo é seguro; frear tarde despacharia um prestador.
# ===========================================================================

# Subserviços auto e a intenção (usada pelo cérebro p/ escolher a opção do menu).
_AUTO_SUBSERVICE_LABELS = {
    "guincho": "guincho (reboque)",
    "bateria": "recarga de bateria / pane elétrica",
    "pneu": "troca de pneu (borracheiro)",
    "chaveiro": "chaveiro para o veículo",
}

# Slots mínimos por subserviço auto. placa/veículo vêm da InfoCap (server-side).
_AUTO_SLOTS_COMMON = ["titular_cpf", "veiculo_placa", "local_atual", "problema_descricao", "quando", "telefone_contato"]
_AUTO_SUBSERVICES = {
    "guincho": {"required_slots": _AUTO_SLOTS_COMMON + ["local_destino"]},
    "bateria": {"required_slots": _AUTO_SLOTS_COMMON},
    "pneu": {"required_slots": _AUTO_SLOTS_COMMON},
    "chaveiro": {"required_slots": _AUTO_SLOTS_COMMON},
}

# QUEM ESPERA NA RUA, E QUEM NÃO ESPERA.
#
# Guincho, bateria, pneu e chaveiro acontecem ONDE o carro parou: a seguradora
# pergunta o nome de quem vai acompanhar o serviço, e sem esse nome o corredor
# trava no meio da conversa.
#
# 📊 Vidro não. O próprio `_VIDROS_SLOTS` já tira o `local_atual` com a nota
# "VIDRO NÃO É REBOQUE… não se pergunta onde o veículo está" — o reparo é
# agendado, e ninguém fica esperando na rua. Exigir `pessoa_no_local` para vidro
# faria o produto perguntar ao segurado exatamente o que a decisão de projeto
# mandou não perguntar.
#
# `pane_seca` entra: é o guincho por outro nome, e o motor já canonicaliza.
_SUBSERVICOS_COM_ALGUEM_NO_LOCAL = ["guincho", "bateria", "pneu", "chaveiro"]

# 🔴 E QUEM ESPERA NA RUA PRECISA TER NOME -- 22/08/2026.
#
# 📊 Achado pelo conferidor de respostas (P-084-14): **9 passos em 6
#    corredores** exigem `pessoa_no_local`, e NADA preenchia esse slot. Nem
#    constante de subservico, nem derivacao, nem coleta, nem padrao do motor.
#
# 🔴 E o par de telas mostra o tamanho do buraco:
#
#      URA: "E a pessoa que esta no local para acompanhar?"
#      NOS: "Nao"                                    <- passo `pessoa_no_local`
#      URA: "Qual e o nome de quem estara no local?"
#      NOS: <SILENCIO>                               <- o slot nao existe
#
#    O corredor diz "nao sou eu" e emudece quando perguntam quem e. E a mesma
#    familia dos 2min22 de 19/08 -- passo que exige slot sem origem fica CALADO.
#
# ⚠️ A resposta "Nao" esta CERTA e nao muda: o WhatsApp e da CORRETORA, e
#    quem espera na rua e o segurado. O que faltava era a corretora dizer QUEM.
#
# ⚠️ E `vidros` continua de fora, pela razao ja escrita acima: o reparo de
#    vidro e AGENDADO, e ninguem fica esperando na rua.
for _sv_local in _SUBSERVICOS_COM_ALGUEM_NO_LOCAL:
    _AUTO_SUBSERVICES[_sv_local]["required_slots"] = (
        list(_AUTO_SUBSERVICES[_sv_local]["required_slots"]) + ["pessoa_no_local"])

# ---------------------------------------------------------------------------
# DESFECHO do corredor (SPEC-063, 03/08/2026)
# ---------------------------------------------------------------------------
# Até aqui todo corredor tinha um só fim possível: chegar ao protocolo. Vidros
# provou que isso é falso. Na Porto, o fluxo de vidro TERMINA num formulário; na
# Zurich, numa orientação. Sem nomear esse desfecho, o motor ficaria esperando
# um protocolo que nunca vem, e o atendimento morreria em "monitorando".
OUTCOME_ABRE = "abre"            # vai até o protocolo (padrão de todo subserviço)
OUTCOME_ENCAMINHA = "encaminha"  # entrega link/orientação ao segurado e ENCERRA

# VIDRO NÃO É REBOQUE. Não se pergunta onde o veículo está nem para onde levar:
# ou o prestador vai até o veículo, ou o veículo vai à oficina de vidro na data
# combinada. Os slots saem de `_AUTO_SLOTS_COMMON` **menos** `local_atual` —
# derivação explícita para que ninguém precise conferir duas listas:
#   titular_cpf · veiculo_placa · problema_descricao (o dano) · quando (a data)
#   · telefone_contato
_VIDROS_SLOTS = [s for s in _AUTO_SLOTS_COMMON if s != "local_atual"]
_VIDROS_LABEL = "conserto ou troca de vidro"

# ---------------------------------------------------------------------------
# APELIDOS DE SUBSERVIÇO — um nome canônico por trabalho
# ---------------------------------------------------------------------------
# `pane seca` é o caso que obriga esta tabela a existir.
#
# 📊 Evidência de URA (`ura_maps` status='observed', 03/08/2026): NENHUMA das 10
# seguradoras tem opção própria de pane seca. Allianz e Alfa dizem
# "*3* - Guincho para *pane mecânica*"; a Zurich lista "pane seca" DENTRO da
# assistência 24h, junto de reboque e socorro mecânico; Bradesco, HDI e Yelum
# usam "Pane ou Defeito", genérico. Não há um único menu em que "pane seca"
# seja uma tecla.
#
# Declarar um subserviço `pane_seca` obrigaria a inventar essa tecla — e o
# corredor responderia à URA uma opção que não existe na tela. Um menu inventado
# é pior que subserviço nenhum. Então pane seca ENTRA PELO GUINCHO, e o
# classificador do Atlas (`infer_ramo_servico`, que já devolve "pane_seca")
# chega aqui e é traduzido, sem um segundo classificador para divergir.
_SUBSERVICE_ALIASES = {
    "pane_seca": "guincho", "pane seca": "guincho", "paneseca": "guincho",
    "combustivel": "guincho", "falta de combustivel": "guincho",
    "sem combustivel": "guincho",
    # o segurado fala no singular, e às vezes fala da peça
    "vidro": "vidros", "para-brisa": "vidros", "parabrisa": "vidros",
    "para brisa": "vidros", "retrovisor": "vidros",
    # residencial: um nome por trabalho. A Porto chama de "elétrica" e
    # "hidráulica" o que a Allianz e a HDI chamam de eletricista e encanador.
    "eletrodomestico": "eletrodomesticos", "eletrica": "eletricista",
    # 🔴 Como o segurado FALA — SPEC-082. Ele nunca diz "maquina_de_lavar":
    # diz "minha máquina de lavar parou", "a lavadora não centrifuga",
    # "lava roupa quebrada". Sem estes apelidos, `canonical_subservice`
    # devolve o proprio texto, `subservices` nao acha, e o acionamento morre
    # antes de comecar.
    "maquina de lavar": "maquina_de_lavar",
    "maquina de lavar roupa": "maquina_de_lavar",
    "maquina de lavar roupas": "maquina_de_lavar",
    "maquina lavar": "maquina_de_lavar",
    "lavadora": "maquina_de_lavar",
    "lavadora de roupa": "maquina_de_lavar",
    "lavadora de roupas": "maquina_de_lavar",
    "lava roupa": "maquina_de_lavar",
    "lava roupas": "maquina_de_lavar",
    "lava e seca": "maquina_de_lavar",
    "maquina de lavar e secar": "maquina_de_lavar",
    "hidraulica": "encanador", "encanamento": "encanador",
    "desentupidor": "desentupimento",
}


def canonical_subservice(subservice: str) -> str:
    """Nome canônico do subserviço: 'pane seca' → 'guincho', 'vidro' → 'vidros'.

    Sem apelido conhecido, devolve o próprio nome em minúsculas — NUNCA um
    palpite. Nome desconhecido continua desconhecido, e vira handoff lá na
    frente (`subservice_supported`)."""
    raw = str(subservice or "").strip().lower()
    if not raw:
        return ""
    return _SUBSERVICE_ALIASES.get(_norm(raw), raw)


def _ativar_vidros(playbook: Dict[str, Any], *, menu_value: str, outcome: str,
                   referral: Optional[Dict[str, Any]] = None) -> None:
    """Liga `vidros` NUMA seguradora — só onde o rótulo do menu foi observado.

    Chamar isto é uma afirmação de evidência: existe menu capturado, e ele diz
    exatamente `menu_value`. Seguradora sem essa captura NÃO recebe a chamada, e
    por isso `subservice_supported(pb, "vidros")` devolve False lá."""
    playbook.setdefault("subservices", {})["vidros"] = {
        "required_slots": list(_VIDROS_SLOTS),
        "outcome": outcome,
        **({"referral": dict(referral)} if referral else {}),
    }
    playbook.setdefault("subservice_menu_map", {})["vidros"] = menu_value
    playbook.setdefault("subservice_labels", {})["vidros"] = _VIDROS_LABEL


# Resumo estruturado do pedido (aberto ao cair no atendente humano da seguradora).
_AUTO_OPENING_TEMPLATE = (
    "Ola, aqui e a corretora. Preciso de {subservice_label} para o veiculo do nosso segurado.\n"
    "Placa: {veiculo_placa}\n"
    "Veiculo: {veiculo_descricao}\n"
    "Titular: {titular_nome} (CPF/CNPJ {titular_cpf})\n"
    "Local do veiculo: {local_atual}\n"
    "Destino: {local_destino}\n"
    "O que houve: {problema_descricao}\n"
    "Quando: {quando}\n"
    "Contato no local: {pessoa_no_local} - {telefone_contato}"
)

# O PROMPT SE CONTRADIZIA SOBRE A UNICA DECISAO IRREVERSIVEL QUE EXISTE.
#
# 📊 Medido em 05/08/2026. Este texto entra no prompt do acionamento
# apresentado ao modelo como "escrita por quem observou esta seguradora — VALE
# MAIS QUE A SUA INTUICAO" (insurer_dispatch_service.py). E ele dizia
# "NAO confirme". Enquanto isso, 772 caracteres acima, a regra 3 do bloco
# `system` dizia "CONFIRME com a opcao afirmativa".
#
# Duas ordens opostas, no mesmo prompt, sobre abrir ou nao abrir um guincho de
# verdade — com `DISPATCH_FINALIZE_MODE=live`.
#
# A frase de nao-confirmar nasceu quando o modo padrao era `test` e o Founder
# fazia as provas no proprio celular. O modo virou `live` e o texto ficou. E o
# Founder decidiu, em 05/08/2026, com todas as letras:
#
#   "Ele precisa CONFIRMAR o acionamento com inteligencia e voltar pra avisar o
#    segurado do que ficou decidido, sem errar, sem travar e SEM PEDIR
#    APROVACAO DE NINGUEM. Ele e o responsavel pelo atendimento."
#
# Entao a orientacao passa a mandar confirmar — e a protecao deixa de ser
# "nao confirme" (que so adiava o trabalho para um humano) e passa a ser
# **CONFERIR ANTES**. Uma checagem explicita e verificavel vale mais que uma
# proibicao, porque a proibicao so garante que nada acontece.
#
# ⚠️ O freio de teste NAO sai daqui: `DISPATCH_FINALIZE_MODE` continua sendo
# quem decide se a confirmacao chega a ser enviada. Prompt nao e trava.
_AUTO_HUMAN_PHASE_GUIDANCE = (
    "Voce conduz, EM NOME DA CORRETORA, um acionamento de assistencia AUTO no WhatsApp da seguradora. "
    "Pode ser a URA (menu numerado ou botoes) ou um atendente humano. Responda menus escolhendo a opcao "
    "coerente com o subservico/dados do caso; responda pedidos de dado com o valor exato do caso "
    "(placa, CPF, endereco, telefone). Endereco/local: use o que o cliente informou; nao invente.\n"
    "QUANDO A SEGURADORA PEDIR PARA CONFIRMAR E ABRIR O SERVICO: voce CONFIRMA. "
    "Voce e o responsavel por este acionamento e nao precisa de aprovacao de ninguem. "
    "Antes de confirmar, confira no resumo que a seguradora mostrou: (1) a placa e o veiculo sao os do caso; "
    "(2) o servico e o que o segurado pediu; (3) o endereco de origem e o que o segurado informou; "
    "(4) se houver destino, e o que o segurado informou. "
    "Se os quatro conferem, confirme com a opcao afirmativa. "
    "Se ALGUM divergir, NAO confirme: corrija com o dado certo do caso, ou responda NAO_SEI se nao houver o dado. "
    "Confirmar com dado errado abre o servico errado, e isso nao se desfaz.\n"
    "Use SOMENTE dados do caso, nunca invente numeros/protocolos/prazos. "
    "Se realmente nao der pra deduzir, responda exatamente: NAO_SEI."
)

# Captura comum de protocolo/OS + link de acompanhamento (auto).
# `protocol` é `_ANCORA_DE_PROTOCOLO` — a mesma que o residencial usa. Ela subiu
# para o topo do arquivo quando o corredor residencial da Allianz precisou dela.
# Zurich agenda com "prevista para o dia X às Y"; Porto/Allianz dão ETA em minutos.
_AUTO_CAPTURE_ANCHORS = {
    "protocol": _ANCORA_DE_PROTOCOLO,
    "schedule": r"(?:agendad?[ao]?|prevista?)\s+para\s+(?:o\s+dia\s+)?\*?(\d{1,2}/\d{1,2}/\d{2,4})\*?(?:\s*(?:[àa]s|,)?\s*\*?(\d{1,2}[:h]\d{0,2}))?",
    "eta": r"(?:previs[ãa]o(?:\s+de\s+chegada)?\s*:?|previsto para ser realizado[^\n]{0,20}?em|em at[ée])\s*(?:at[ée]\s+)?(\d{1,3})\s*min",
    "tracking_link": r"(https?://\S+)",
}

# Instruções fixas ao cliente para guincho/serviço no local.
_AUTO_CLIENT_INSTRUCTIONS_GUINCHO = [
    "Aguarde em local seguro, com as chaves e o documento do veículo.",
    "É preciso alguém maior de 18 anos no local para acompanhar o guincho.",
    "Você vai receber um SMS/link com a previsão de chegada do prestador.",
]
_AUTO_CLIENT_INSTRUCTIONS_LOCAL = [
    "Aguarde em local seguro próximo ao veículo.",
    "É preciso alguém maior de 18 anos no local para acompanhar o serviço.",
]

_AUTO_HANDOFF_TRIGGERS = [
    r"sinistro", r"colis[ãa]o", r"acidente", r"n[ãa]o localizamos", r"n[ãa]o encontrei .* ap[óo]lice",
    r"ap[óo]lice .* (?:vencid|cancelad|inativ)", r"sem cobertura", r"n[ãa]o (?:tem|possui) cobertura",
]


def _auto_playbook(insurer_key: str, contact_ref: str, ura_steps, finalize_anchors, *, version: int = 1) -> Dict[str, Any]:
    """Fábrica de playbook auto: mesma espinha, URA/freio por seguradora."""
    return {
        "playbook_id": f"{insurer_key}-auto-whatsapp",
        "version": version,
        "insurer_key": insurer_key,
        "line_kind": "auto",
        "channel": "whatsapp",
        "insurer_contact_ref": contact_ref,
        "description": f"Assistência 24h AUTO {insurer_key} via WhatsApp (guincho/bateria/pneu/chaveiro).",
        "subservices": {k: dict(v) for k, v in _AUTO_SUBSERVICES.items()},
        "opening_template": _AUTO_OPENING_TEMPLATE,
        "subservice_labels": dict(_AUTO_SUBSERVICE_LABELS),
        "ura_steps": ura_steps,
        "finalize_anchors": finalize_anchors,
        "human_phase_guidance": _AUTO_HUMAN_PHASE_GUIDANCE,
        "capture_anchors": dict(_AUTO_CAPTURE_ANCHORS),
        # A lista do GUINCHO só vale para o guincho.
        #
        # 📊 `_AUTO_CLIENT_INSTRUCTIONS_LOCAL` existia desde sempre e nunca foi
        # usada: a fábrica injetava a de guincho em TODOS os subserviços. Quem
        # pedia troca de pneu recebia "aguarde com as chaves e o documento do
        # veículo, e alguém para acompanhar o GUINCHO".
        #
        # Instrução errada não é só feia: faz o segurado procurar documento que
        # não vai precisar e esperar um caminhão que não vem.
        "client_instructions": list(_AUTO_CLIENT_INSTRUCTIONS_GUINCHO),
        "client_instructions_por_subservico": {
            "guincho": list(_AUTO_CLIENT_INSTRUCTIONS_GUINCHO),
            "bateria": list(_AUTO_CLIENT_INSTRUCTIONS_LOCAL),
            "pneu": list(_AUTO_CLIENT_INSTRUCTIONS_LOCAL),
            "chaveiro": list(_AUTO_CLIENT_INSTRUCTIONS_LOCAL),
        },
        "handoff_triggers": list(_AUTO_HANDOFF_TRIGGERS),
        "unknown_step_policy": "adaptive_then_handoff",
    }


# --- Allianz auto (fluxo REAL 05/03/2026 minerado por completo) --------------------
_ALLIANZ_FAMILY_AUTO_STEPS = [
    # Família Allianz/Alfa (mesmo fornecedor de bot): URA numerada.
    # 🔴 DUAS CÓPIAS DA MESMA VERDADE, UMA CORRIGIDA E OUTRA VENCIDA — 22/08/2026.
    #
    # O `cpf_anterior` do ALLIANZ_RESIDENCIAL foi consertado em 18/08 (a URA de 2026
    # escreve "Que bom que voltou! ... com o CPF/CNPJ 030.###?"). A correção **nunca
    # chegou aqui**, e esta lista é a que alfa e allianz-auto leem.
    # 📊 A âncora antiga casa ZERO no acervo; a nova casa 1 tela na alfa e 2 na allianz.
    #
    # ⚠️ E a resposta "2" é a mesma pela mesma razão: o WhatsApp é da CORRETORA e
    #    atende N clientes. O CPF lembrado é o do atendimento ANTERIOR — aceitar
    #    aciona a apólice de outra pessoa.
    {"step": "cpf_anterior",
     "anchor": (r"em nossa [úu]ltima conversa,? utilizamos o cpf|"
                r"que bom que voltou.{0,80}cpf|continuar nossa conversa com o cpf"),
     "reply": "2",
     "notes": "URA lembra o CPF do último atendimento — SEMPRE re-identificar "
              "(2=inserir outro). 📊 A redação de 2026 é 'Que bom que voltou!'."},
    {"step": "atendimento_recente", "anchor": r"atendimento realizado recentemente", "reply": "2",
     "notes": "1-mesmo atendimento 2-abrir novo serviço"},
    {"step": "pedir_cpf", "anchor": r"digite o \*?cpf\*? ou \*?cnpj\*? do\(a\)? titular", "reply": "{titular_cpf}",
     "requires": ["titular_cpf"]},
    {"step": "pedir_placa", "anchor": r"preciso da \*?placa\*? do ve[íi]culo", "reply": "{veiculo_placa}",
     "requires": ["veiculo_placa"]},
    {"step": "confirmar_veiculo", "anchor": r"confirme o ve[íi]culo para atendimento", "reply": "1",
    "constante_justificada": (
        "📊 A tela ECOA o veículo que a própria URA encontrou pela placa que NÓS enviamos. Confirmar é confirmar o que mandamos. ⚠️ Quando há MAIS DE UM veículo na apólice a tela é outra, e ali o passo é `escolher_veiculo`, com `dynamic: vehicle_by_plate`."),
     "dynamic": "vehicle_by_plate", "fallback_adaptive": True,
     "notes": "escolhe a opção cuja placa mascarada casa com a placa do caso (JC#-###9 ↔ JCL9A59); sem match → adaptativo"},
    {"step": "confirmar_telefone", "anchor": r"deseja adicionar outro n[úu]mero", "reply": "{telefone_adicionar_opcao}",
     "requires": ["telefone_adicionar_opcao"], "notes": "1=Sim (informa telefone_contato) 2=Não (usa o registrado)"},
    {"step": "informar_telefone", "anchor": r"informe \*?o n[úu]mero de celular completo\*? com ddd",
     "reply": "{telefone_contato}", "requires": ["telefone_contato"]},
    {"step": "telefone_anotado", "anchor": r"anotei seu n[úu]mero", "reply": "1"},
    {"step": "tipo_veiculo", "anchor": r"seu ve[íi]culo [ée]:\s*\|?\s*\*?1\s*-\s*automotor", "reply": "1",
    "constante_justificada": (
        "📊 1-Automotor (gasolina/etanol/diesel) ou híbrido · 2-Elétrico. 🔴 IDENTIFICADA, NÃO RESOLVIDA: a frota elétrica existe e o corredor não sabe distinguir. Registrado em PENDENCIAS — hoje '1' cobre a maioria medida, e errar aqui muda o EQUIPAMENTO de reboque."),
     "notes": "1-automotor(combustão/híbrido) 2-elétrico. Default 1; caso elétrico, adaptativo"},
    {"step": "menu_servico_auto", "anchor": r"o que voc[êe] precisa\??\s*\|?\s*\*?1", "reply": "{servico_opcao}",
     "requires": ["servico_opcao"],
     "notes": "1-pane elétrica/bateria 3-guincho pane mecânica 4-guincho sinistro 6-pneu 7-chaveiro"},
    # 🔴 A ÂNCORA SÓ CONHECIA QUATRO OFÍCIOS, E A URA NOMEIA O SERVIÇO NA TELA.
    #    📊 telas "para quando precisa d..." no acervo, com o passo que casava ANTES:
    #         allianz [quando] "...do *reboque para pane mecânica*"        3 ses  ✅
    #         allianz [quando] "...do profissional para *recarga*"         2 ses  ✅
    #         allianz [ORFA]   "...do *borracheiro para troca de pneu*"    3 ses  🔴
    #         allianz [ORFA]   "E para quando precisa do *Eletricista*?"   1 ses  🔴
    #         alfa    [ORFA]   "...do *borracheiro para troca de pneu*"    1 ses  🔴
    #    🔴 CONTROLE POSITIVO (a linha que dá direito à conclusão): as 3 telas que já
    #       casavam continuam casando. Ampliar é seguro; trocar não é.
    {"step": "quando",
    "constante_justificada": (
        "📊 'Agora' x 'Agendar'. O corredor só é acionado quando a corretora abriu um caso de assistência — que é, por definição, agora. ⚠️ Se um dia existir rota de AGENDAMENTO, esta constante vira slot."),
     "anchor": (r"para quando precisa d[oa] \*?(?:reboque|guincho|servi[çc]o|profissional|"
                r"borracheiro|chaveiro|t[ée]cnico|socorro|eletricista|encanador)"), "reply": "1",
     "notes": "1-Agora 2-Agendar; urgência é o default do corredor"},
    {"step": "oferta_mecanico", "anchor": r"continuar com a solicita[çc][ãa]o do guincho", "reply": "2",
     "notes": "URA oferece mecânico no lugar do guincho — o serviço é o que o CLIENTE pediu (2=continuar guincho)"},
    {"step": "rodas_travadas", "anchor": r"rodas? travadas?", "reply": "2",
     "notes": "default Não (2); se o caso indicar roda travada, o adaptativo assume"},
    {"step": "acesso_reboque", "anchor": r"local que o reboque consegue acessar", "reply": "1",
     "notes": "1-Sim; se o caso indicar acesso difícil, o adaptativo assume"},
    {"step": "pcd_criancas", "anchor": r"pessoa com defici[êe]ncia, crian[çc]a, gestante ou idoso", "reply": "2",
     "notes": "default Não; se houver no caso, o adaptativo assume"},
    {"step": "referencia_local", "anchor": r"informe uma refer[êe]ncia do local", "reply": "{ponto_referencia}",
     "notes": "texto livre; default 'não tem'"},
    {"step": "destino_menu", "anchor": r"preciso saber o endere[çc]o de destino", "reply": "1",
     "notes": "1-Oficina mecânica ou outro endereço 2-Não sei (só estado/cidade)"},
    {"step": "destino_uf", "anchor": r"informe a \*?uf\*? \(sigla do estado\) \*?do destino", "reply": "{destino_uf}",
     "fallback_adaptive": True, "notes": "UF deduzida de local_destino pelo parser"},
    {"step": "destino_cidade", "anchor": r"e qual a cidade", "reply": "{destino_cidade}", "fallback_adaptive": True},
    {"step": "destino_logradouro", "anchor": r"informe apenas o nome do logradouro", "reply": "{destino_logradouro}",
     "fallback_adaptive": True},
    {"step": "destino_numero", "anchor": r"qual o n[úu]mero do endere[çc]o \(ou quil[ôo]metro", "reply": "{destino_numero}",
     "fallback_adaptive": True, "notes": "só dígitos ('Km 205' é rejeitado — o parser extrai '205')"},
    {"step": "confirmar_atendimento", "anchor": r"podemos confirmar o atendimento", "reply": "1",
     "notes": "confirmação FINAL (RESUMO). Só alcançada em modo LIVE — no teste o freio cancela antes."},
    # NOOP POR ÚLTIMO — a ordem é a regra, e ela quase custou o corredor.
    #
    # A âncora inclui "opção inválida|vamos tentar novamente|aguarde em
    # local seguro". 📊 Quando a URA reenvia o menu NA MESMA mensagem do
    # aviso — que é o comportamento típico — este noop casava primeiro e o
    # corredor ficava MUDO diante de um menu que sabia responder. A URA
    # encerra por inatividade e o acionamento morre sem erro no log.
    #
    # `match_ura_step` devolve o PRIMEIRO que casa. Noop é o "não sei o que
    # fazer com isto" — tem de ser o ÚLTIMO consultado, como já é na
    # família HDI (`aguarde_fila` é o último de lá).
    {"step": "avisos_informativos",
     "anchor": (r"termo de privacidade|dicas importantes para conseguir te atender|fique tranquilo, vamos te ajudar|"
                r"vale lembrar:|voc[êe] sabia\?|op[çc][ãa]o inv[áa]lida|vamos tentar novamente|"
                r"precisando estamos por aqui|agradece o seu contato|aguarde em local seguro"),
     "reply": "", "noop": True,
     "notes": "mensagens informativas/erro da URA — NUNCA responder (o adaptativo respondia 'Ciente, pode prosseguir' e quebrava o menu)"},

]
_ALLIANZ_FAMILY_FINALIZE = [
    # Texto REAL 2026: RESUMO → "Podemos confirmar o atendimento?"
    r"podemos confirmar o atendimento",
    r"dados a seguir est[ãa]o corretos", r"posso confirmar", r"deseja confirmar",
    r"confirm\w* (?:o|a) (?:agendamento|abertura|solicita)",
]

ALLIANZ_AUTO_WHATSAPP_V1 = _auto_playbook(
    "allianz", "allianz_assistencia_24h",
    ura_steps=[
        {"step": "menu_tipo_seguro", "anchor": r"assist[êe]ncia 24h para qual seguro", "reply": "1",
        "constante_justificada": (
            "📊 A ROTA JÁ DIZ o ramo. `menu_tipo_seguro` só existe dentro de um playbook de auto ou de residencial — a tecla não escolhe nada que o caso não tenha decidido antes de o corredor abrir."),
         "notes": "1-Auto/Moto/Caminhão 2-Residência 3-Vida 4-Viagem 5-Outros → Auto"},
    ] + [dict(s) for s in _ALLIANZ_FAMILY_AUTO_STEPS] + [
        {"step": "endereco_origem_menu", "anchor": r"selecione o endere[çc]o onde est[áa] o ve[íi]culo", "reply": "3",
        "constante_justificada": (
            "📊 1-Informar endereço manual x compartilhar localização. O corredor NÃO manda pin nativo do WhatsApp — digitar é o único caminho que ele consegue percorrer."),
         "notes": "Allianz 2026: 1-endereço da apólice 2-compartilhar localização 3-informar manual "
                  "(Alfa NÃO tem a opção 3 — lá o adaptativo decide)"},
    ],
    finalize_anchors=list(_ALLIANZ_FAMILY_FINALIZE),
)
ALLIANZ_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "3", "bateria": "1", "pneu": "6", "chaveiro": "7",
}
ALLIANZ_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "SAIR"  # URA aceita SAIR a qualquer momento

# --- Porto (fluxo REAL 25/03/2026: listas/botões — responder o RÓTULO; números
# são REJEITADOS: "Não entendi sua resposta. Selecione o botão abaixo") ----------
PORTO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "porto", "porto_assistencia_24h",
    ura_steps=[
        # A URA lembra o último cliente e abre saudando ele pelo nome. 1ª vez que o
        # menu raiz aparecer: re-identificar ("Informar outro CPF/CNPJ"); quando ele
        # reaparecer (já com NOSSO cliente), seguir para "Seguro Auto" (reply_repeat).
        {"step": "menu_raiz", "anchor": r"escolha a op[çc][ãa]o desejada",
         "reply": "Informar outro CPF/CNPJ", "reply_repeat": "Seguro Auto",
         "reply_if_step_done": {"step": "pedir_cpf", "reply": "Seguro Auto"},
         "notes": "menu raiz: se JÁ digitamos o CPF nesta sessão o cliente exibido é o nosso → Seguro Auto direto; senão re-identifica (nunca acionar no CPF lembrado do cliente anterior)"},
        {"step": "pedir_cpf", "anchor": r"(?:informe|digite) o (?:seu )?\*?cpf ou cnpj\*?", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"], "notes": "2026: 'digite o seu *CPF ou CNPJ*'"},
        {"step": "menu_como_ajudar", "anchor": r"como eu posso te ajudar\?.*servi[çc]os para ve[íi]culo",
         "reply": "Serviços para veículo", "notes": "lista: Serviços para veículo / residência / Sinistro / ..."},
        {"step": "confirmar_veiculo", "anchor": r"quer atendimento para o ve[íi]culo", "reply": "Sim",
        "constante_justificada": (
            "📊 A tela ECOA o veículo que a própria URA encontrou pela placa que NÓS enviamos. Confirmar é confirmar o que mandamos. ⚠️ Quando há MAIS DE UM veículo na apólice a tela é outra, e ali o passo é `escolher_veiculo`, com `dynamic: vehicle_by_plate`."),
         "notes": "URA mostra o veículo da apólice (botões Sim/Não/Voltar)"},
        {"step": "menu_seguro_auto", "anchor": r"localizei o seu \*?seguro auto", "reply": "1",
         "notes": "variante antiga numerada — manter"},
        {"step": "menu_atendimento", "anchor": r"de que atendimento voc[êe] precisa", "reply": "Novo serviço",
        "constante_justificada": (
            "📊 'Novo serviço' entre acompanhar/cancelar/consultar. O corredor existe para ABRIR — acompanhar e cancelar são outros trabalhos, e 'Cancelar serviço' é a opção 1 em uma das variantes: tecla errada aqui CANCELA um serviço já aberto."),
         "notes": "lista: Novo serviço / Acompanhar / Cancelar / ..."},
        {"step": "menu_servico", "anchor": r"o que voc[êe] precisa\?.*guincho", "reply": "{servico_texto}",
         "requires": ["servico_texto"],
         "notes": "responder o RÓTULO completo. 📊 lista real 03/08/2026: Guincho (reboque) / Bateria / "
                  "Troca de pneu / Conserto de vidro (Inclui retrovisor, farol ou lanterna) / "
                  "Chaveiro para o veículo / Táxi"},
        {"step": "bateria_submenu", "anchor": r"entendi\. o que voc[êe] precisa",
         "reply": "Recarga de bateria",
         "notes": "submenu após 'Bateria' (teste real 12/07: Recarga de bateria / Bateria nova / Na garantia — travava aqui)"},
        # VIDROS na Porto NÃO abre chamado aqui — DESFECHO = encaminha.
        # 📊 URA real 03/08/2026, três mensagens seguidas:
        #   "Certo. Para conserto ou reparo de vidro, retrovisor, farol ou
        #    lanterna, é necessário *preencher o formulário* de sinistro de
        #    vidros abaixo"
        #   "https://porto.vc/reparovidros"
        #   "Não se preocupe, esse acionamento *para vidros* não irá afetar a
        #    sua classe de bônus."
        # O link vem numa mensagem SOZINHA — por isso ele é capturado por
        # `capture_anchors.tracking_link` (qualquer http), e não por uma âncora
        # que exija a palavra 'formulário' na mesma mensagem. A URL NÃO fica
        # escrita aqui: quem a entrega é a seguradora, na hora.
        {"step": "vidros_formulario",
         "anchor": (r"necess[áa]rio \*?preencher o formul[áa]rio\*? de sinistro de vidros|"
                    r"para conserto ou reparo de vidro,? retrovisor,? farol ou lanterna"),
         "reply": "", "noop": True, "referral": True, "outcome": OUTCOME_ENCAMINHA,
         "notes": "não responder à URA: o trabalho passa a ser ENTREGAR o formulário ao segurado e encerrar"},
        {"step": "necessidade_guincho", "anchor": r"op[çc][ãa]o que descreve melhor a sua necessidade",
         "reply": "Remoção de veículo",
         "notes": "Remoção de veículo (pane) · 'Envolvimento em acidente' = sinistro → handoff antes de chegar aqui"},
        {"step": "menu_quando", "anchor": r"para quando voc[êe] precisa que esse servi[çc]o", "reply": "Tenho urgência",
         "notes": "botões: Tenho urgência / Agendar. A frase 'confirmada somente após a finalização' é COLETA."},
        {"step": "complemento", "anchor": r"digite ent[ãa]o um \*?complemento", "reply": "não tem",
         "notes": "complemento do endereço; sem complemento = 'não tem'"},
        {"step": "ponto_referencia",
         "anchor": r"(?:o local tem|pode me informar) algum \*?ponto de refer[êe]ncia",
         "reply": "{ponto_referencia}",
         "notes": "só a PERGUNTA — o RESUMO da solicitação também contém 'Ponto de referência:' e não deve disparar (teste 12/07 respondeu 'não tem' ao resumo)"},
        {"step": "destino_sabe", "anchor": r"onde o guincho deve levar seu ve[íi]culo", "reply": "Sim",
         "notes": "guincho: já sabemos o destino (local_destino do caso)"},
        {"step": "no_local", "anchor": r"[ée] voc[êe] que est[áa] no local para (?:acompanhar|aguardar)", "reply": "Sim",
         "notes": "quem está no local acompanha; dados de contato ajustáveis no menu de revisão"},
        {"step": "pode_ligar", "anchor": r"posso te ligar no n[úu]mero abaixo", "reply": "Sim",
         "notes": "autoriza contato telefônico do prestador"},
        {"step": "endereco_livre", "anchor": r"digite o endere[çc]o completo do local", "reply": "{local_atual}",
         "reply_repeat": "{local_destino}", "requires": ["local_atual"], "fallback_adaptive": True,
         "notes": "Porto aceita endereço em texto livre; 1ª vez = origem, 2ª = destino do guincho"},
        # 🔴 ESTA ÂNCORA ROUBAVA A TELA DO TELEFONE — 22/08/2026.
        #    📊 `est[áa] correto\s*\?` casa **7** telas: 6 do endereço e
        #       **"O número está correto? {TELEFONE} *1* - Sim *2* - Não"**.
        #       Responder "Sim" ali confirma um telefone que ninguém conferiu —
        #       e é para esse número que o prestador liga quando não acha a casa.
        #    🔴 CONTROLE: com `^`, casa exatamente 6. `match_ura_step` compila
        #       com IGNORECASE|DOTALL e **sem** MULTILINE, então `^` é o início
        #       da mensagem inteira — que é onde a tela do endereço começa e a
        #       do telefone não.
        {"step": "numero_correto", "anchor": r"^o n[úu]mero est[áa] correto", "reply": "1",
         "notes": "📊 1 tela / 1 sessão. Vem ANTES de `endereco_correto` de propósito."},
        {"step": "endereco_correto", "anchor": r"^est[áa] correto\s*\?", "reply": "Sim",
         "notes": "confirma o geocode do endereço QUE NÓS digitamos"},
        # 🔴 UMA ANCORA, DUAS TELAS, DOIS ROTULOS -- achado do conferidor de
        #    respostas em 22/08/2026.
        #
        # 📊 "Como voce quer prosseguir?"   -> Confirmar solicitacao / Mudar
        #                                        localizacao / ...       ✅ o rotulo existe
        # 📊 "Posso confirmar sua solicitacao?"
        #        Sim
        #        Nao, alterar endereco
        #        Sair e nao agendar                                  🔴 "Confirmar
        #                                                              solicitacao" NAO
        #                                                              esta entre as tres
        #
        # ⚠️ E a URA nao trava: ela REJEITA. A confirmacao nao acontece, o
        #    acionamento fica pendurado do lado da seguradora, e o nosso lado
        #    acha que confirmou. E a mesma familia do "Sair e nao agendar" da
        #    azul, ja documentada -- a segunda vez que o MESMO erro aparece por
        #    uma ancora que serve duas telas.
        {"step": "confirmar_solicitacao_sim",
         "anchor": r"posso confirmar sua solicita[çc][ãa]o", "reply": "Sim",
         "notes": "📊 A tela lista Sim / Nao, alterar endereco / Sair e nao agendar."},
        {"step": "confirmar_solicitacao", "anchor": r"como voc[êe] quer prosseguir",
         "reply": "Confirmar solicitação",
         "notes": "confirmação FINAL. Só alcançada em modo LIVE — no teste o freio cancela antes. "
                  "⚠️ A tela de 'Posso confirmar sua solicitacao?' tem OUTROS rotulos e "
                  "passo proprio, logo acima."},
        # NOOP POR ÚLTIMO — mesma regra da família Allianz.
        #
        # 📊 A âncora deste noop inclui "falta pouco para finalizarmos", e o
        # passo `confirmar_solicitacao` vinha DEPOIS dele. Se a Porto mandar
        # as duas frases juntas — "Falta pouco para finalizarmos! Como você
        # quer prosseguir?" — o corredor cala na TELA FINAL.
        #
        # Em modo teste o freio salva. Em modo LIVE, não: o acionamento
        # morreria a um clique de terminar, sem erro nenhum.
        {"step": "aguarde",
         "anchor": r"aguarde um momento|que bom ter voc[êe] de volta|aguarde enquanto solicito|localizei o endere[çc]o|para informar o endere[çc]o, voc[êe] tem essas op[çc][õo]es|compartilhe a sua localiza[çc][ãa]o|preencha o formul[áa]rio abaixo|falta pouco para finalizarmos",
         "reply": "", "noop": True, "notes": "mensagens de espera/instrução — não responder"},

    ],
    finalize_anchors=[
        # Texto REAL 2026: "Como você quer prosseguir? Confirmar solicitação ..."
        r"como voc[êe] quer prosseguir",
        r"posso confirmar sua solicita[çc][ãa]o",
        # URA antiga (manter por segurança):
        r"posso continuar o agendamento",
        r"gostaria de alterar alguma informa[çc][ãa]o",
        r"confirmar o agendamento",
    ],
)
PORTO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Guincho (reboque)", "bateria": "Bateria", "pneu": "Troca de pneu", "chaveiro": "Chaveiro para veículo",
}
PORTO_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair e não agendar"

# --- Família YELUM/HDI (MESMO bot white-label "Assistência 24 horas"; Yelum =
# ex-Liberty, grupo HDI desde 2024). Fluxo REAL COMPLETO 16/03/2026 (Yelum,
# 100% bot até o protocolo) + 28/01/2026 (HDI). Botões por rótulo; timeout 12min.
# PONTO DE NÃO-RETORNO: "quer o atendimento para agora ou prefere agendar?" —
# responder Agora/Agendar ABRE o serviço na hora. O destino é seguro de informar.

# ...e essa pergunta tem TRÊS redações reais. 📊 Banco de produção, 03/08/2026,
# `observed_events` ILIKE '%prefere agendar%' (auto E residencial da família):
#
#   "Você está solicitando o atendimento *para* agora ou prefere agendar..."  hdi 9
#   "Você quer o atendimento *para* agora ou prefere agendar..."       hdi 2 · yelum 17
#   "Você precisa do atendimento agora ou prefere agendar..."          hdi 1 · yelum 4
#
# A terceira NÃO tem o "para" — e era a única que a âncora literal
# `atendimento para agora ou prefere agendar` não pegava. O freio ficava furado
# exatamente na tela que ABRE o serviço na hora. 📊 A ocorrência da HDI
# (02/06/2026, sessão 26c0546f) é RESIDENCIAL: a mesma sessão traz "Para esse CPF
# localizamos o serviço de *ENCANADOR*" e "Ela não possui mais utilizações de
# encanador".
#
# O "para" vira opcional, e a âncora vira UMA constante: ela é usada no passo de
# URA e nos freios de três playbooks, e três cópias literais divergem no dia em
# que a seguradora escrever a quarta redação.
#
# 🔴 E O NEGRITO DO WHATSAPP QUASE CUSTOU UM PRESTADOR DESPACHADO SEM QUERER.
#
# 📊 03/08/2026: a âncora era `atendimento (?:para )?agora ou prefere agendar` —
# sem escapar o asterisco. As duas redações mais frequentes mandam `*para*` em
# NEGRITO, e o asterisco chega literal (nada no pipeline o remove).
#
#   "...o atendimento *para* agora ou prefere agendar..."   28 de 33 ocorrências
#
# Ou seja: **o freio não disparava em 85% das vezes**, e justamente na tela que
# este arquivo chama de PONTO DE NÃO-RETORNO. Sem freio, o caso caía no cérebro
# adaptativo — que tem `quando_agora → "Agora"` no guia de fluxo. A trava
# determinística virava uma frase de prompt.
#
# E estava verde no CI porque as fixtures do teste escreviam a mensagem **sem os
# asteriscos**, embora o docstring do próprio teste os citasse.
#
# As três palavras que a seguradora pode negritar ganham `\*?`, que é a
# convenção já usada em 93 âncoras deste arquivo.
_HDI_FAMILY_AGORA_OU_AGENDAR = (
    r"\*?atendimento\*? (?:\*?para\*? )?\*?agora\*? ou prefere agendar"
)

_YELUM_FAMILY_STEPS = [
    {"step": "identificacao_dado",
     "anchor": r"informe \*?apenas um dos dados|informe \*?um dos dados abaixo|informe somente o \*?cpf ou cnpj\*? do t[íi]tular",
     "reply": "{titular_cpf}", "requires": ["titular_cpf"],
     "notes": "entrada: CPF/CNPJ do segurado OU placa (frota usa CNPJ)"},
    {"step": "continuar_com_placa", "anchor": r"identifiquei em seu cadastro a placa", "reply": "Automóvel",
     "notes": "após CPF, a URA acha a placa e pergunta veículo ou residencial"},
    {"step": "informar_nome", "anchor": r"informe o seu nome ou como gostaria de ser chamad", "reply": "Atendimento",
     "notes": "nome de quem opera o canal (a corretora)"},
    {"step": "informar_placa", "anchor": r"qual a placa do ve[íi]culo", "reply": "{veiculo_placa}",
     "requires": ["veiculo_placa"]},
    {"step": "perfil", "anchor": r"em qual dessas op[çc][õo]es voc[êe] se enquadra", "reply": "Sou corretor(a)",
     "notes": "agimos em nome da corretora"},
    {"step": "pessoa_no_local", "anchor": r"[ée] a pessoa que est[áa] (?:no )?local para acompanhar", "reply": "Não"},
    {"step": "nome_pessoa_local", "anchor": r"qual [ée] o nome da pessoa que est[áa] no local",
     "reply": "{pessoa_no_local}", "requires": ["pessoa_no_local"],
     "only_subservices": _SUBSERVICOS_COM_ALGUEM_NO_LOCAL,
     "notes": "quem acompanha o servico NO LOCAL. Vidro nao entra: o reparo e agendado, ninguem espera na rua."},
    {"step": "telefone_local", "anchor": r"n[úu]mero de (?:celular|telefone)\*? com ddd da pessoa que est[áa] no local",
     "reply": "{telefone_contato}", "requires": ["telefone_contato"]},
    # 🔴 A ÂNCORA QUE EXIGIA DÍGITOS DE UM NÚMERO QUE VEM MASCARADO.
    #    📊 `o n[úu]mero de telefone \d+ est[áa] correto` casa **ZERO** telas nos
    #       QUATRO corpora da família (yelum-auto, hdi-auto, yelum-resid, hdi-resid).
    #       A tela existe em todos: "O número de telefone {TELEFONE} está correto?"
    #       — 31 ocorrências-sessão somadas. O `\d+` casaria em produção, onde há
    #       dígitos; no corpus versionado, não. E um passo que só funciona fora do
    #       teste é um passo que ninguém pode provar.
    #    🔴 CONTROLE: a redação ampliada casa as duas formas (mascarada e com
    #       dígitos) e nada além delas — `.{0,24}` não atravessa a frase.
    {"step": "telefone_confirma", "anchor": r"o n[úu]mero de telefone .{0,24}est[áa] correto",
     "reply": "Sim",
     "notes": "📊 4 corredores da família · 31 ocorrências-sessão. Ampliar contém a "
              "antiga; trocar não conteria."},
    {"step": "cor_menu", "anchor": r"informar a cor do ve[íi]culo de placa", "reply": "Outros"},
    {"step": "cor_texto", "anchor": r"qual a cor do ve[íi]culo de placa", "reply": "{veiculo_cor}",
     "notes": "campo livre; default 'não sei'"},
    {"step": "rodovia", "anchor": r"(?:o ve[íi]culo|saber se o ve[íi]culo) est[áa] em uma rodovia", "reply": "{rodovia}",
     "notes": "Sim/Não conforme local_atual; default Não"},
    {"step": "o_que_aconteceu", "anchor": r"pode me dizer o que aconteceu", "reply": "{servico_opcao}",
     "requires": ["servico_opcao"],
     "notes": "guincho→Pane ou Defeito · bateria→Recarga de bateria · pneu→Pneu Furado · chaveiro→Problema com a chave · colisão=SINISTRO (handoff antes)"},
    # 🔴 UMA CONSTANTE ESCOLHIA A PANE DO SEGURADO POR ELE — 22/08/2026.
    #
    # 📊 O menu tem NOVE opções: Problemas elétricos · Luzes do painel ·
    #    Vazamento · Superaquecimento · Problemas no motor · Embreagem ·
    #    Câmbio · Não sei · Mais opções. O passo respondia "Problemas no motor",
    #    fixo, nas nove.
    #
    # 🔴 E é essa escolha que a URA usa para separar REBOQUE de MECÂNICO NO
    #    LOCAL. A sessão real de socorro mecânico da HDI (71caf82f, 01/06/2026,
    #    protocolo 9662631) apertou **"Problemas elétricos"** — e recebeu um
    #    mecânico. Com a constante, ela teria pedido um guincho.
    #
    # A tradução do relato é o trabalho do corredor: o segurado descreve com as
    # palavras dele, e o corredor converte para a tecla da seguradora.
    {"step": "pane_detalhe", "anchor": r"selecione a op[çc][ãa]o que condiz com a pane",
     "reply": "{pane_detalhe_opcao}", "requires": ["pane_detalhe_opcao"],
     "fallback_adaptive": True,
     "notes": "📊 9 opções. Vem do RELATO, nunca fixo — a tecla decide reboque x "
              "mecânico no local. Sem relato utilizável, o adaptativo lê a tela."},
    {"step": "endereco_como", "anchor": r"op[çc][õo]es para informar o endere[çc]o onde o ve[íi]culo est[áa]",
     "reply": "Digitar endereço", "notes": "variante jan/2026: Digitar endereço / Compartilhar / Informar o CEP / Não sei"},
    {"step": "endereco_direto_2026",
     "anchor": r"para informar o endere[çc]o onde o ve[íi]culo est[áa],? \*?escolha apenas uma",
     "reply": "{local_atual}", "requires": ["local_atual"],
     "notes": "URA jul/2026: aceita o endereço COMPLETO digitado — sem clique (validado no teste real 12/07)"},
    {"step": "descreva_situacao", "anchor": r"descreva em suas palavras", "reply": "{problema_descricao}",
     "requires": ["problema_descricao"], "fallback_adaptive": True,
     "notes": "campo livre após 'Não sei' na pane — descrição real do caso"},
    {"step": "endereco_rua", "anchor": r"digite \*?somente a rua", "reply": "{local_rua}",
     "fallback_adaptive": True, "notes": "rua deduzida de local_atual pelo parser; sem dedução → adaptativo"},
    {"step": "endereco_numero", "anchor": r"qual (?:[ée] )?o \*?n[úu]mero\*?\s*\?", "reply": "{local_numero}",
     "reply_repeat": "{destino_numero}", "fallback_adaptive": True,
     "notes": "1ª vez = nº da origem; 2ª vez = nº do destino"},
    {"step": "endereco_bairro", "anchor": r"qual (?:[ée] )?o \*?bairro", "reply": "{local_bairro}",
     "reply_repeat": "{destino_bairro}", "fallback_adaptive": True},
    {"step": "endereco_cidade", "anchor": r"qual (?:[ée] )?a \*?cidade", "reply": "{local_cidade}",
     "reply_repeat": "{destino_cidade}", "fallback_adaptive": True},
    {"step": "endereco_estado", "anchor": r"qual o \*?estado", "reply": "{local_uf}",
     "reply_repeat": "{destino_uf}", "fallback_adaptive": True},
    {"step": "confirma_endereco", "anchor": r"voc[êe] confirma o endere[çc]o", "reply": "Sim",
     "notes": "resumo geocodificado do QUE NÓS digitamos (origem e destino) — confirmar"},
    {"step": "complemento_ref", "anchor": r"quais s[ãa]o o complemento e/?ou refer[êe]ncia", "reply": "{ponto_referencia}",
     "notes": "default 'não tem'"},
    {"step": "garagem", "anchor": r"o ve[íi]culo est[áa] em uma garagem", "reply": "Não",
     "notes": "default Não; subsolo real → adaptativo"},
    {"step": "cambio_rodas", "anchor": r"c[âa]mbio\*? ou as \*?rodas\*? est[ãa]o travadas", "reply": "Não",
     "notes": "default Não; travado de verdade → adaptativo"},
    {"step": "eletrico_hibrido", "anchor": r"el[ée]trico ou h[íi]brido", "reply": "Não"},
    {"step": "rebaixado", "anchor": r"o ve[íi]culo [ée] rebaixado", "reply": "Não"},
    {"step": "situacao_risco", "anchor": r"situa[çc][õo]es de risco", "reply": "Nenhuma das anteriores",
     "notes": "se o caso indicar risco real, o adaptativo assume"},
    {"step": "ocupantes", "anchor": r"ocupantes tem alguma das particularidades|algu[ée]m da lista abaixo no local",
     "reply": "Nenhuma das anteriores"},
    {"step": "destino_como", "anchor": r"para onde devemos levar o ve[íi]culo", "reply": "Digitar endereço",
     "notes": "guincho: informar o destino do caso (rua/nº/bairro/cidade/UF do parser)"},
    {"step": "deseja_continuar", "anchor": r"deseja continuar (?:este|com o) atendimento", "reply": "Sim"},
    {"step": "falar_analista", "anchor": r"gostaria de falar com um de nossos analistas", "reply": "Sim",
     "notes": "72h/pós-atendimento (teste real 12/07): SIM → fila → analista humano recebe o resumo do caso e abre a nova solicitação"},
    {"step": "quando_agora", "anchor": _HDI_FAMILY_AGORA_OU_AGENDAR, "reply": "Agora",
     "notes": "PONTO DE NÃO-RETORNO (abre na hora). Só alcançado em modo LIVE — no teste o freio cancela antes."},
    {"step": "aguarde_fila",
     "anchor": (r"ainda n[ãa]o identificamos a sua resposta|voc[êe] est[áa] na fila|alto volume de atendimentos|"
                r"alta demanda de servi[çc]os|aguarde (?:um momento|s[óo] mais)|te transfiro para um|"
                r"transferido para fila|dicas (?:r[áa]pidas|sobre como funciona)|seja bem-?vindo ao atendimento|"
                r"estamos prontos para seguir com sua solicita|s[óo] preciso de mais algumas informa|"
                r"enviaremos o servi[çc]o de|foi abert[ao] com sucesso|no final desta conversa|"
                r"orienta[çc][õo]es importantes|problema na comunica[çc][ãa]o com o sistema|"
                r"necess[áa]rio falar com um de nossos especialistas|identificamos que voc[êe] deseja falar|"
                r"foi aberta uma assist[êe]ncia para a placa|n[ãa]o h[áa] mais nenhuma solicita[çc][ãa]o em andamento"),
     "reply": "", "noop": True, "notes": "fila/aviso/informativo — NÃO responder (o bot manda rajadas)"},
]
_YELUM_FAMILY_FINALIZE = [
    # Único gate real: responder 'Agora'/'Agendar' ABRE o serviço imediatamente.
    _HDI_FAMILY_AGORA_OU_AGENDAR,
    r"podemos confirmar", r"deseja confirmar",
]

# ===========================================================================
# FORMULÁRIO NATIVO (WhatsApp Flow) — a tela que não aceita texto
# ===========================================================================
# 📊 Desde 18/06/2026 a família HDI/Yelum substituiu as telas de condição do
# veículo por um **WhatsApp Flow** (aplicativo dentro do WhatsApp). A mensagem
# que o abre é sempre a mesma, e ela NÃO tem botões:
#
#   "Para que a remoção do veículo ocorra sem imprevistos, precisamos entender
#    o local e as condições do veículo."
#
# 📊 `observed_events` (banco de produção, consultado em 03/08/2026): essa
# mensagem aparece 4 vezes — hdi 18/06, hdi 15/07, hdi 18/07 e yelum 18/07 — e
# são os 4 acionamentos mais recentes da família. TODOS param nela: o corredor
# reconhece o marcador `[FORMULARIO NATIVO]` do parser de interativas e cai em
# `handoff_triggers` → needs_human. Nenhum deles chegou ao protocolo.
#
# O que destrava é RESPONDER o formulário por código. E responder exige o
# SCHEMA — quais telas, quais campos, e o **id** de cada opção. Ele está
# capturado: o clique humano de 18/07/2026 (`msg_type='flow_reply'`,
# `source='live'`) trouxe, dentro de `wa_flow_response_params.response_message`,
# o formulário inteiro com `data-source` de cada componente.
#
# Este bloco é a transcrição desse schema. É DADO versionado, como o resto dos
# corredores: nada aqui foi deduzido de tela parecida, e onde a captura veio
# vazia (ver `rb_Ocupantes` id "4") o vazio ficou vazio.
#
# UM REGISTRO, DUAS REFERÊNCIAS: HDI e Yelum são o MESMO bot white-label e usam
# o MESMO `flow_id`. O registro é um objeto só, apontado pelos dois playbooks —
# `native_flows` de um É `native_flows` do outro (`is`, não `==`). Duplicar
# criaria dois schemas para divergirem no dia em que a HDI mudar uma opção.
NATIVE_FLOW_CONDICOES_VEICULO = "857030507196739"

# Âncora da mensagem que ABRE o flow (o corpo vem antes do marcador do parser).
NATIVE_FLOW_PROMPT_ANCHOR = r"precisamos entender o local e as condi[çc][õo]es do ve[íi]culo"

_FLOW_CONDICOES_VEICULO_V2: Dict[str, Any] = {
    "flow_id": NATIVE_FLOW_CONDICOES_VEICULO,
    "flow_name": ("Automóvel - Detalhes do atendimento (veículo, local e ocupantes) V2 "
                  "[Redução de perguntas]"),
    "insurer_family": ("hdi", "yelum"),
    "prompt_anchor": NATIVE_FLOW_PROMPT_ANCHOR,
    # Procedência da transcrição — quem duvidar refaz a query.
    "observed": {
        "source": "observed_events.interactive → extra.paramsJSON → "
                  "wa_flow_response_params.response_message",
        "insurer_key": "hdi",
        "msg_type": "flow_reply",
        "event_source": "live",
        "wa_timestamp": "2026-07-18T21:51:52Z",
    },
    "screens": [
        {
            "id": "scr_SituacaoVeiculo",
            "title": "Situação do veículo",
            "components": [
                {
                    "name": "rb_EmGaragemOuEstacionamento",
                    "type": "RadioButtonsGroup",
                    "label": "O veículo está em uma garagem ou estacionamento?",
                    "required": True,
                    # `"visible": "${data.isVisibleGaragem}"` — bandeira que só o
                    # servidor da seguradora resolve. Offline não dá para avaliar,
                    # e o lado seguro é tratar como VISÍVEL: assim o campo continua
                    # obrigatório e o caso PEDE o dado, em vez de omitir em silêncio
                    # um campo que o formulário pode estar exigindo.
                    "visible_if": {"kind": "data", "key": "isVisibleGaragem"},
                    "slot": "veiculo_em_garagem",
                    # SEM padrão, de propósito. Esta resposta é o que decide se
                    # `rb_NivelDaRua` — que escolhe o EQUIPAMENTO — chega a ser
                    # perguntada. Chutar "Não" aqui seria a porta dos fundos da
                    # regra que proíbe chutar o nível da rua.
                    "default": None,
                    "options": [{"id": "1", "title": "Sim"}, {"id": "0", "title": "Não"}],
                    # Apelidos só onde a palavra JÁ significa a opção. "prédio",
                    # "condomínio" e "shopping" ficaram de fora: carro parado na
                    # rua em frente ao prédio não está em garagem nenhuma.
                    "aliases": {
                        "sim": "1", "s": "1", "garagem": "1", "estacionamento": "1",
                        "subsolo": "1",
                        "nao": "0", "n": "0", "rua": "0", "via publica": "0",
                        "na rua": "0", "estacionado na rua": "0",
                    },
                },
                {
                    "name": "rb_NivelDaRua",
                    "type": "RadioButtonsGroup",
                    "label": "Em relação ao nível da rua, onde o veículo está?",
                    "required": True,
                    # `"visible": "`${form.rb_EmGaragemOuEstacionamento} == '1'`"` —
                    # esta DÁ para avaliar offline, porque o form é o que estamos
                    # montando. Veículo fora de garagem: a tela não aparece, o campo
                    # não é exigido e não entra na resposta.
                    "visible_if": {"kind": "form", "field": "rb_EmGaragemOuEstacionamento",
                                   "equals": "1"},
                    "slot": "veiculo_nivel_rua",
                    # SEM padrão: escolhe o EQUIPAMENTO enviado (plataforma, asa
                    # delta, munck). Errar aqui manda o guincho que não sobe a rampa.
                    "default": None,
                    "options": [
                        {"id": "1", "title": "Subsolo",
                         "description": "Acesso por rampa interna ou níveis abaixo do solo."},
                        {"id": "2", "title": "Acima do nível da rua",
                         "description": "Acesso por rampa íngreme ou acima do nível da via"},
                        {"id": "3", "title": "Nível da rua - com restrição de acesso",
                         "description": "Acesso direto pela rua, mas com restrições de espaço ou manobra"},
                        {"id": "4", "title": "Nível da rua - com acesso livre",
                         "description": "Acesso direto pela rua, com livre espaço para remoção e manobra"},
                    ],
                    # "rampa" NÃO é apelido de nada: aparece na descrição do
                    # subsolo ("rampa interna") E na do acima do nível ("rampa
                    # íngreme}"). Palavra ambígua num campo que escolhe equipamento
                    # tem de ficar sem resposta, não virar moeda ao ar. Pelo mesmo
                    # motivo "nível da rua" sozinho não resolve: serve às opções 3 e 4.
                    "aliases": {
                        "subsolo": "1", "garagem subterranea": "1", "abaixo do solo": "1",
                        "acima": "2", "acima do nivel": "2", "elevado": "2", "rampa ingreme": "2",
                        "restricao": "3", "com restricao": "3", "restricao de acesso": "3",
                        "livre": "4", "acesso livre": "4",
                    },
                },
                {
                    "name": "ckb_SituacoesVeiculo",
                    "type": "CheckboxGroup",
                    "label": "O veículo possui alguma das características abaixo?",
                    "required": True,
                    "multiple": True,
                    "slot": "veiculo_situacoes",
                    # COM padrão: é a mesma resposta que o corredor já dava por
                    # texto nos passos `cambio_rodas`, `rebaixado` e
                    # `eletrico_hibrido` ("Não" em cada um) — e "nenhuma" é o que
                    # ela vira quando as três viram uma tela só.
                    "default": ["nenhuma_opcoes"],
                    "none_option": "nenhuma_opcoes",
                    "options": [
                        {"id": "cambio_travado", "title": "Câmbio ou rodas travadas"},
                        {"id": "veiculo_rebaixado", "title": "Veículo rebaixado"},
                        {"id": "veiculo_blindado", "title": "Veículo blindado"},
                        {"id": "eletrico_hibrido", "title": "Veículo elétrico ou híbrido"},
                        {"id": "nenhuma_opcoes", "title": "Nenhuma das opções"},
                    ],
                    "aliases": {
                        "cambio travado": "cambio_travado", "rodas travadas": "cambio_travado",
                        "roda travada": "cambio_travado", "travado": "cambio_travado",
                        "rebaixado": "veiculo_rebaixado",
                        "blindado": "veiculo_blindado",
                        "eletrico": "eletrico_hibrido", "hibrido": "eletrico_hibrido",
                        "nenhuma": "nenhuma_opcoes", "nenhum": "nenhuma_opcoes",
                        "nao": "nenhuma_opcoes", "nada": "nenhuma_opcoes",
                    },
                },
            ],
        },
        {
            "id": "scr_InformacoesLocal",
            "title": "Informações do Local",
            "components": [
                {
                    "name": "rb_InformacoesLocal",
                    "type": "RadioButtonsGroup",
                    "label": "Qual é a situação do local onde você está?",
                    "required": True,
                    "slot": "local_situacao",
                    # SEM padrão: muda a PRIORIDADE do atendimento. Responder
                    # "Local Seguro" por preguiça de perguntar é rebaixar, no
                    # escuro, o caso de quem está parado num lugar perigoso.
                    "default": None,
                    # No JSON o `data-source` é `${data.dt_InformacoesLocal}`; os
                    # valores vieram resolvidos em `screenState.data`.
                    "options": [
                        {"id": "6", "title": "Local Seguro"},
                        {"id": "2", "title": "Local escuro ou mal iluminado"},
                        {"id": "3", "title": "Área com pouca circulação de pessoas"},
                    ],
                    # Onde há dúvida, o apelido puxa para o lado MAIS protegido:
                    # "deserto"/"isolado" viram "pouca circulação", que sobe a
                    # prioridade. O caminho contrário — inferir "seguro" — é o que
                    # não se faz.
                    "aliases": {
                        "seguro": "6", "local seguro": "6",
                        "escuro": "2", "mal iluminado": "2", "sem iluminacao": "2",
                        "pouca circulacao": "3", "deserto": "3", "isolado": "3",
                    },
                },
            ],
        },
        {
            "id": "scr_IdentificacaoOcupantes",
            "title": "Identificação dos ocupantes",
            "components": [
                {
                    "name": "rb_Ocupantes",
                    "type": "RadioButtonsGroup",
                    "label": "Há alguém no local com as dependências abaixo?",
                    "required": True,
                    "slot": "ocupantes_particularidade",
                    # COM padrão: é literalmente a resposta que o corredor já dava
                    # no passo de texto `ocupantes` ("Nenhuma das anteriores").
                    "default": "1",
                    "options": [
                        {"id": "2", "title": "Criança"},
                        {"id": "3", "title": "Idoso"},
                        # 📊 O TÍTULO VEIO VAZIO NA CAPTURA. O JSON real traz
                        # {"id":"4","title":""}. Inventar "Gestante" aqui seria
                        # exatamente o defeito que este arquivo proíbe em menu de
                        # URA — só que pior, porque ninguém reconferiria depois.
                        # Sem título não há apelido, e por isso um caso que diga
                        # "gestante" NÃO casa com opção nenhuma: vira `missing` e
                        # o humano clica. Sai do escuro quando houver captura com
                        # o título preenchido.
                        {"id": "4", "title": "", "titulo_ausente": True},
                        {"id": "5", "title": "Pessoa com deficiência"},
                        {"id": "6", "title": "Cirurgia Recente"},
                        {"id": "1", "title": "Nenhuma das anteriores"},
                    ],
                    "aliases": {
                        "crianca": "2", "bebe": "2", "menor": "2",
                        "idoso": "3", "idosa": "3",
                        "pcd": "5", "deficiente": "5", "deficiencia": "5",
                        "cirurgia": "6", "cirurgia recente": "6", "operado": "6",
                        "nenhuma": "1", "nenhum": "1", "ninguem": "1", "nao": "1",
                    },
                },
            ],
        },
    ],
}

# O registro. Um objeto, indexado por flow_id — os dois playbooks apontam para
# ELE, não para cópias dele.
_NATIVE_FLOWS_FAMILIA_HDI_YELUM: Dict[str, Dict[str, Any]] = {
    NATIVE_FLOW_CONDICOES_VEICULO: _FLOW_CONDICOES_VEICULO_V2,
}


HDI_AUTO_WHATSAPP_V1 = _auto_playbook(
    "hdi", "hdi_assistencia_24h",
    ura_steps=[
        {"step": "menu_auto_ou_resid",
         "anchor": r"assist[êe]ncia para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia|para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia",
         "reply": "🚗 Automóvel", "notes": "botões com emoji: '🚗 Automóvel' / '🏠 Residência'"},
    ] + [dict(s) for s in _YELUM_FAMILY_STEPS],
    finalize_anchors=list(_YELUM_FAMILY_FINALIZE),
)
HDI_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Pane ou Defeito", "bateria": "Recarga de bateria",
    "pneu": "Pneu Furado", "chaveiro": "Problema com a chave",
}
HDI_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair"  # 'Digite Sair para encerrar'
# O schema do flow. 📊 E, desde 03/08/2026, o TRANSPORTE também existe:
# `/send/interactiveResponse` foi provada no ar, com o embrulho
# DocumentWithCaption — ver O-FORMULARIO-NATIVO-RESOLVIDO.md.
#
# Por isso o gatilho `r"formulario nativo"` saiu daqui. Ele existia porque "ter o
# schema não é ter o canal" — e era verdade. Mantê-lo agora desviaria para humano
# exatamente o caso que o produto passou a saber resolver sozinho, e o trabalho
# das últimas semanas não renderia nada.
#
# O que protege no lugar dele NÃO é uma regra escrita aqui — é o motor:
# `montar_resposta_de_flow` recusa responder formulário que não conhece, ou com
# campo obrigatório sem valor, e devolve `ok=False`. Aí sim o acionamento pausa,
# com o dossiê e o motivo. **Fail-closed por construção, não por lista.**
HDI_AUTO_WHATSAPP_V1["native_flows"] = _NATIVE_FLOWS_FAMILIA_HDI_YELUM

# --- Yelum (ex-Liberty, grupo HDI): v3 minerado do fluxo REAL COMPLETO de
# 16/03/2026 (conversa "Liberty Fácil Assist" = Yelum rebatizada; 100% bot até o
# protocolo 9415275). Mesmos passos da família HDI + variantes antigas próprias.
YELUM_AUTO_WHATSAPP_V1 = _auto_playbook(
    "yelum", "yelum_assistencia_24h",
    ura_steps=[
        {"step": "menu_auto_ou_resid",
         "anchor": r"assist[êe]ncia para (?:o )?(?:seu|sua) \*?(?:autom[óo]vel|casa)\*? ou \*?resid[êe]ncia\*?|sua \*?casa\*? ou \*?carro\*?",
         "reply": "Automóvel", "notes": "variante antiga usa botões Casa/Carro"},
    ] + [dict(s) for s in _YELUM_FAMILY_STEPS] + [
        {"step": "podemos_confirmar", "anchor": r"podemos confirmar", "reply": "Sim",
         "notes": "confirmação final (modo LIVE)"},
    ],
    finalize_anchors=list(_YELUM_FAMILY_FINALIZE),
)
YELUM_AUTO_WHATSAPP_V1["version"] = 3
YELUM_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Pane ou Defeito", "bateria": "Recarga de bateria",
    "pneu": "Pneu Furado", "chaveiro": "Problema com a chave",
}
YELUM_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair"  # 'Digite Sair para encerrar'
# O gatilho `r"formulario nativo"` saiu daqui pelo mesmo motivo da HDI: o canal
# passou a existir e foi provado. Quem recusa formulário desconhecido é o motor.
# MESMO objeto do corredor da HDI (mesmo bot, mesmo flow_id). `is`, não `==`.
YELUM_AUTO_WHATSAPP_V1["native_flows"] = _NATIVE_FLOWS_FAMILIA_HDI_YELUM

# ==========================================================================
# 🔴 TOKIO — A SEGURADORA QUE NÃO ABRE NADA NESTE CANAL — 22/08/2026
# ==========================================================================
#
# 📊 O corredor tinha UM passo, e ele casava **0 de 28** telas em auto e
#    **0 de 17** em residencial: a tela "você é segurado, prestador ou
#    corretor" não existe em nenhuma das 45 telas do corpus.
#    CONTROLE: uma âncora que sabemos casar ("digite o cpf/cnpj") casa 1 —
#    o teste CONSEGUE dar ≥1, então o zero é do passo, não do método.
#
# 🔴 E o defeito de fundo é maior que o corredor vazio. O fluxo real, IDÊNTICO
#    nas 7 sessões de auto e nas 4 de residencial:
#
#      1. "Digite o CPF/CNPJ do titular do Seguro."
#      2. "Consegui identificar seu Seguro!"
#      3. "Seu protocolo de atendimento é 68977599"     <- turno 3 de 8 a 11
#      4. menu de serviços do Seguro Automóvel
#      5. "Clique no link abaixo para solicitar ASSISTÊNCIA AUTOMÓVEL 24H E
#          GUINCHO: https://autoatendimento.tokiomarine.com.br/..."   <- O FIM
#
#    A tokio **entrega um LINK e encerra**. Os 4 subserviços herdam
#    `_AUTO_SUBSERVICES` sem `outcome`, isto é `OUTCOME_ABRE` — "vai até o
#    protocolo". Ele nunca vai.
#
# 🔴 PIOR: `_ANCORA_DE_PROTOCOLO` colhe o CARIMBO DE ENTRADA (7 de 7 sessões,
#    turno 3, antes de qualquer escolha de serviço) e o corredor encerra
#    entregando "assistência aberta, protocolo 68977599" — enquanto **nada
#    foi aberto**. É o número do chat, não do chamado.
#    Corroborado de fora: `zonas_do_acervo.FRONTEIRAS["tokio"]` está VAZIO,
#    com a nota já escrita "a tokio sai por link ou telefone, não transfere
#    no fio". Duas medições independentes, a mesma conclusão.
_TOKIO_REFERRAL = {
    "kind": "orientacao",
    "closes_as": "resolvido_por_encaminhamento",
    "link_capture": "tracking_link",
    "client_message": (
        "A Tokio Marine NÃO abre guincho, chaveiro, pane nem pneu pelo WhatsApp: ela "
        "entrega um LINK de autoatendimento e encerra. Repasse ao segurado o link que "
        "a seguradora mandou NESTA conversa — nunca um endereço de memória. "
        "🔴 E avise que o número recebido no início é PROTOCOLO DE ATENDIMENTO DO CHAT, "
        "não número de serviço: não há chamado aberto até ele usar o link."
    ),
}
TOKIO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "tokio", "tokio_assistencia_24h",
    ura_steps=[
        {"step": "pedir_cpf",
         "anchor": (r"digite o cpf/cnpj do titular do seguro|"
                    r"me informe o cpf/cnpj para come[çc]armos"),
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "📊 7 de 7 sessões, 2 redações. É a porta de entrada obrigatória."},
        {"step": "menu_servicos_auto",
         "anchor": r"menu de servi[çc]os do (?:seguro )?autom[óo]vel",
         "reply": "Guincho/Assist.24h",
         "notes": "📊 7 de 7 sessões. LISTA — responde-se o RÓTULO; dígito é rejeitado. "
                  "⚠️ É a MESMA tecla para guincho, bateria, pneu e chaveiro: a tokio "
                  "não separa os quatro neste menu."},
        {"step": "encaminha_assistencia",
         "anchor": r"para solicitar (?:ou acompanhar )?\*?assist[êe]ncia (?:autom[óo]vel|auto)",
         "reply": "", "noop": True,
         "notes": "📊 3 sessões. É o FIM da rota. Sem este passo o corredor fica "
                  "'monitorando' um protocolo que não vem."},
        {"step": "sinistro_em_andamento",
         "anchor": r"possui um processo de sinistro em andamento",
         "reply": "", "noop": True,
         "notes": "📊 2 telas / 3 sessões. INFORMATIVA: a URA segue para o menu logo "
                  "depois. 🔴 Vem ANTES de qualquer leitura de handoff — ver a nota "
                  "do `handoff_triggers` abaixo."},
        {"step": "algo_mais", "anchor": r"posso te ajudar em algo mais",
         "reply": "Encerrar atendimento",
         "notes": "📊 7 de 7 sessões. ⚠️ Na MAPFRE a mesma pergunta tem outros rótulos "
                  "(lá é 'Não'). Duas seguradoras, duas respostas."},
        # 🔴 O noop vai por ÚLTIMO: `match_ura_step` devolve o primeiro que casa,
        #    e uma alternativa larga na frente emudece menu que o corredor sabe ler.
        {"step": "avisos_informativos",
         "anchor": (r"consegui identificar seu seguro|vou iniciar seu atendimento|"
                    r"voc[êe] ainda est[áa] comigo|estou finalizando este atendimento|"
                    r"conhe[çc]a o super app da tokio|em uma escala de 0 a 10|"
                    r"seu protocolo de atendimento [ée]|"
                    r"n[ãa]o entendi, selecione uma op[çc][ãa]o"),
         "reply": "", "noop": True,
         "notes": "📊 14 telas distintas / 7 sessões. NENHUMA pede resposta. "
                  "🔴 'seu protocolo de atendimento é' entra AQUI como noop — e isso "
                  "NÃO impede a captura: quem colhe é `capture_anchors`, e é lá que o "
                  "carimbo ganhou nome próprio (`ticket_de_entrada`)."},
    ],
    finalize_anchors=[r"posso confirmar", r"deseja confirmar", r"confirmar? (?:o|a) (?:agendamento|abertura)"],
)
TOKIO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "Guincho/Assist.24h", "bateria": "Guincho/Assist.24h", "pneu": "Guincho/Assist.24h", "chaveiro": "Guincho/Assist.24h"}

# 🔴 OS QUATRO PASSAM A ENCAMINHAR. Hoje os quatro diziam OUTCOME_ABRE.
for _sv in ("guincho", "bateria", "pneu", "chaveiro"):
    TOKIO_AUTO_WHATSAPP_V1["subservices"][_sv]["outcome"] = OUTCOME_ENCAMINHA
    TOKIO_AUTO_WHATSAPP_V1["subservices"][_sv]["referral"] = dict(_TOKIO_REFERRAL)

# 🔴 O CARIMBO DE ENTRADA GANHA NOME PRÓPRIO, e sai de `protocol`.
#    📊 7 de 7 sessões trazem "Seu protocolo de atendimento é NNNNNNNN" no turno 3,
#    ANTES de qualquer escolha. Encerrar um caso com esse número é prometer um
#    chamado que não existe.
TOKIO_AUTO_WHATSAPP_V1["capture_anchors"] = {
    **TOKIO_AUTO_WHATSAPP_V1["capture_anchors"],
    "protocol": (r"(?:ordem\s+de\s+servi[çc]o|\bo\.?s\.?#?(?=\d))\s*#?\s*(\d{5,12})"),
    "ticket_de_entrada": r"(?:o\s+)?seu\s+protocolo\s+de\s+atendimento\s+[ée]\s*(\d{6,12})",
    "tracking_link": r"(https?://autoatendimento\.tokiomarine\.com\.br/\S+)",
}

# 🔴 O GATILHO `sinistro` CRU DERRUBAVA MAIS DA METADE DAS SESSÕES BOAS.
#    📊 A palavra aparece em 14 dos 70 eventos do corpus, em 5 de 7 sessões —
#    incluindo as 3 que terminaram bem. A tela "Verifiquei que você possui um
#    processo de *sinistro em andamento*, já vou deixar aqui onde acompanhar"
#    é INFORMATIVA: a URA continua o menu logo depois.
#    Aqui `sinistro` só é handoff quando a tela PEDE alguma coisa sobre ele.
TOKIO_AUTO_WHATSAPP_V1["handoff_triggers"] = [
    t for t in TOKIO_AUTO_WHATSAPP_V1["handoff_triggers"] if t != r"sinistro"
] + [
    r"abrir (?:um )?sinistro", r"comunicar (?:o )?sinistro",
    r"qual [ée] o n[úu]mero do processo",
]

# --- ALFA (URA gêmea da Allianz — mesmo fornecedor; fluxo REAL 03/02/2026) --------
ALFA_AUTO_WHATSAPP_V1 = _auto_playbook(
    "alfa", "alfa_assistencia_24h",
    ura_steps=[
        {"step": "menu_tipo_seguro", "anchor": r"assist[êe]ncia 24h para qual seguro", "reply": "1",
        "constante_justificada": (
            "📊 A ROTA JÁ DIZ o ramo. `menu_tipo_seguro` só existe dentro de um playbook de auto ou de residencial — a tecla não escolhe nada que o caso não tenha decidido antes de o corredor abrir."),
         "notes": "1-Automóvel/Moto 2-Residencial 3-Outros → Auto"},
    ] + [dict(s) for s in _ALLIANZ_FAMILY_AUTO_STEPS],
    finalize_anchors=list(_ALLIANZ_FAMILY_FINALIZE),
)
ALFA_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "3", "bateria": "1", "pneu": "6", "chaveiro": "7"}
ALFA_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "SAIR"
# Alfa às vezes não abre guincho pelo WhatsApp ("no momento eu não consigo te
# ajudar" → central 4003-2532): vira handoff com o telefone no dossiê.
ALFA_AUTO_WHATSAPP_V1["handoff_triggers"] = ALFA_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    r"n[ãa]o consigo te ajudar",
]

# --- AZUL (grupo Porto, URA própria NUMERADA — fluxo REAL 26/12/2025) -------------
AZUL_AUTO_WHATSAPP_V1 = _auto_playbook(
    "azul", "azul_assistencia_24h",
    ura_steps=[
        # 🔴 O MENU-RAIZ DA AZUL, E OS DOIS PASSOS QUE CASAVAM **ZERO** — 22/08/2026
        #
        # As duas âncoras antigas exigiam a pergunta E a opção na MESMA mensagem.
        # 📊 A URA manda TRÊS bolhas separadas, e nesta ordem:
        #
        #   1. "Olá, sou a atendente virtual da Azul Seguros 👋"       20 msgs / 16 ses
        #   2. "Selecione uma opção, por favor.
        #       Assistência emergencial | Guincho, técnico e chaveiro
        #       Sinistro | Vidros e faróis | Martelinho de ouro | …"   23 msgs / 16 ses
        #   3. "Como eu posso te ajudar?"                             21 msgs / 16 ses
        #
        # 🔴 A pergunta vem numa bolha SEPARADA e **DEPOIS** do menu. E `.` não
        #    atravessa `\n` em Python, então nem o `.*` salvaria.
        #    📊 `menu_inicial` casa 0 telas. `menu_inicial_num` idem — a frase
        #    "Como eu posso te ajudar? 1 - Assistência 24h" tem 0 ocorrências no
        #    acervo INTEIRO. **A porta de entrada da azul nunca abriu por passo.**
        #
        # A âncora nova mora na bolha que traz as OPÇÕES, que é onde a escolha é feita.
        {"step": "menu_inicial_lista",
         "anchor": r"selecione uma op[çc][ãa]o, por favor[\s\S]{0,60}assist[êe]ncia emergencial",
         "reply": "Assistência emergencial",
         "notes": "📊 23 msgs · 16 de 19 sessões · 22/08/2025 a 28/07/2026. É LISTA: "
                  "responde-se o RÓTULO. O [\\s\\S]{0,60} existe porque `.` não cruza "
                  "quebra de linha — a versão com `.*` casava ZERO."},
        {"step": "como_posso_ajudar", "anchor": r"^como eu posso te ajudar\?\s*$",
         "reply": "", "noop": True,
         "notes": "📊 21 msgs / 16 ses. É a pergunta SOZINHA, e chega DEPOIS do menu. "
                  "Cardápio, não escolha."},
        {"step": "saudacao_atendente", "anchor": r"sou a atendente virtual da azul",
         "reply": "", "noop": True, "notes": "📊 20 msgs / 16 sessões."},
        {"step": "pedir_cpf", "anchor": r"informe o \*?cpf ou cnpj\*? do\(a\)? segurad", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"]},
        # 🔴 AQUI A ÂNCORA **E** A RESPOSTA ESTAVAM ERRADAS — 22/08/2026.
        #    📊 "INFORME a cor do veículo"   -> 1 sessão  (lista de 2025)
        #    📊 "SELECIONE a cor do veículo" -> 6 sessões (lista de 2026)  <- órfã
        #    🔴 E `reply: "Outra cor"` só existe na lista de 2025. A de 2026 termina
        #       em "Mais opções | *Não sei a cor*" — e foi "Não sei a cor" que a
        #       sessão real respondeu. Mandar rótulo que não está na tela não trava:
        #       a URA devolve "Não entendi sua resposta" e o turno se perde.
        {"step": "cor_menu", "anchor": r"(?:selecione|informe)(?: agora)? a cor do ve[íi]culo",
         "reply": "{veiculo_cor_rotulo}", "fallback_adaptive": True,
         "notes": "📊 2 telas / 7 sessões. Vem do caso. Sem cor no caso, a tecla honesta "
                  "da lista de 2026 é Não sei a cor; na de 2025 ela NÃO EXISTE e o "
                  "caminho é Outra cor, que abre texto livre (`cor_texto`)."},
        {"step": "cor_texto", "anchor": r"escreva qual a cor", "reply": "{veiculo_cor}",
         "notes": "default 'não sei'"},
        {"step": "menu_atendimento", "anchor": r"de que atendimento voc[êe] precisa", "reply": "1",
        "constante_justificada": (
            "📊 'Novo serviço' entre acompanhar/cancelar/consultar. O corredor existe para ABRIR — acompanhar e cancelar são outros trabalhos, e 'Cancelar serviço' é a opção 1 em uma das variantes: tecla errada aqui CANCELA um serviço já aberto."),
         "notes": "1-Novo serviço"},
        {"step": "menu_servico", "anchor": r"o que voc[êe] precisa\?\s*\|?\s*\*?1\*?\s*-\s*guincho", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "📊 menu real 03/08/2026 (numerado): 1-Guincho (reboque) 2-Bateria 3-Troca de pneu "
                  "4-Chaveiro para o veículo 5-Conserto ou troca de vidro, retrovisor... "
                  "— na Azul vidro é TECLA, e o fluxo segue normal até o protocolo"},
        {"step": "bateria_submenu", "anchor": r"entendi\. o que voc[êe] precisa\?.*recarga de bateria",
         "reply": "Recarga de bateria", "notes": "submenu da bateria: Recarga / Bateria nova / Na garantia"},
        {"step": "quando", "anchor": r"para quando voc[êe] precisa que esse servi[çc]o", "reply": "1",
        "constante_justificada": (
            "📊 'Agora' x 'Agendar'. O corredor só é acionado quando a corretora abriu um caso de assistência — que é, por definição, agora. ⚠️ Se um dia existir rota de AGENDAMENTO, esta constante vira slot."),
         "notes": "1-Tenho urgência (a frase 'confirmada somente após a finalização' faz parte desta COLETA)"},
        # 🔴 ANCORADO NA REDAÇÃO RARA — 1 sessão, enquanto a viva tem 10.
        #    📊 "é você que estARÁ no local"  ->  1 sessão  (2025)
        #    📊 "é você que ESTÁ no local"    -> 10 sessões (2026)  <- órfã até aqui
        #    Ampliar CONTÉM a antiga; trocar não conteria. É a lição que migra.
        {"step": "no_local", "anchor": r"[ée] voc[êe] que est[áa](?:r[áa])? no local para acompanhar", "reply": "2",
         "notes": "1-Sim 2-Não (informamos quem estará). 📊 11 msgs / 11 sessões."},
        {"step": "nome_no_local", "anchor": r"qual [ée] o nome de quem estar[áa] no local", "reply": "{pessoa_no_local}",
         "requires": ["pessoa_no_local"],
         "only_subservices": _SUBSERVICOS_COM_ALGUEM_NO_LOCAL,
         "notes": "quem acompanha o servico NO LOCAL. Vidro nao entra: o reparo e agendado, ninguem espera na rua."},
        # 🔴 Mesma família de defeito: 1 sessão contra 8.
        #    📊 "informe um número de contato. digite no formato" -> 1 sessão (2025)
        #    📊 "informe um *número de celular* com DDD"          -> 8 sessões (2026)
        {"step": "telefone_contato",
         "anchor": (r"informe um n[úu]mero de contato\. digite no formato|"
                    r"informe um \*?n[úu]mero de celular\*? com ddd|"
                    r"e qual [ée] o n[úu]mero de quem est[áa] no local"),
         "reply": "{telefone_contato}", "requires": ["telefone_contato"], "format": "phone_br",
         "notes": "📊 3 telas / 9 sessões. A redação de 2025 pede formato ESTRITO "
                  "(dd) 99999-9999; a de 2026 aceita dígitos com DDD. O motor formata."},
        {"step": "telefone_correto", "anchor": r"o n[úu]mero est[áa] correto", "reply": "1"},
        {"step": "ponto_referencia",
         "anchor": r"(?:o local tem|pode me informar) algum \*?ponto de refer[êe]ncia",
         "reply": "{ponto_referencia}",
         "notes": "só a PERGUNTA (o RESUMO também contém 'Ponto de referência:'); se não houver, 'não tem'"},
        # 🔴 A LARGA ROUBA A ESTREITA -- e por isso a estreita vem PRIMEIRO.
        #    📊 "Posso te ajudar com algo mais? Botao 1: Novo atendimento
        #        Botao 2: Falar com atendente  Botao 3: Encerrar"
        #    "Nao" NAO e opcao dessa tela, e "Falar com atendente" e a tecla que
        #    joga o caso no humano da SEGURADORA -- o oposto do que a SPEC quer.
        {"step": "algo_mais_3botoes",
         "anchor": r"posso te ajudar com algo mais\?[\s\S]{0,80}novo atendimento",
         "reply": "Encerrar",
         "notes": "📊 1 tela. Mesma dupla que a porto ja tem resolvida."},
        {"step": "algo_mais", "anchor": r"posso te ajudar com algo mais", "reply": "Não",
         "notes": "pós-protocolo: encerrar com educação"},
        # 🔴 O RESUMO. Informativo, e por isso NOOP — mas noop com motivo.
        #
        # 📊 04/08/2026, `observed_events` insurer_key='azul': 8 ocorrências de
        # "Antes de confirmar a solicitação, confira as informações 👇" e NENHUM
        # passo casava. Sem passo, a mensagem caía no cérebro adaptativo com o
        # guia dizendo "responda menus escolhendo a opção coerente" — e a única
        # coisa parecida com opção neste texto é o serviço que ele resume.
        # Responder ao resumo é responder à confirmação um passo antes dela.
        {"step": "resumo_solicitacao",
         "anchor": r"antes de confirmar a solicita[çc][ãa]o,? confira as informa[çc][õo]es",
         "reply": "", "noop": True,
         "notes": "RESUMO da Azul — a tela de decisão vem na mensagem SEGUINTE ('Como você quer prosseguir?')"},
        {"step": "confirmar_tudo", "anchor": r"tudo est[áa] correto", "reply": "1",
         "notes": "confirmação FINAL da URA NUMERADA (📊 2 ocorrências, últimas em 26/12/2025). "
                  "Só alcançada em modo LIVE — no teste o freio cancela antes."},
        # 🔴 A TELA QUE ABRE O SERVIÇO — a mesma da Porto, na mesma posição.
        #
        # 📊 04/08/2026: "Como você quer prosseguir? / Confirmar solicitação /
        # Mudar localização atual / Alterar local de destino / Alterar dados de
        # contato / Sair e não agendar" — 8 ocorrências, de 07/04 a 28/07/2026.
        # É LISTA (`interactive.kind = list`): responde-se o RÓTULO.
        #
        # A Azul entrou no grupo Porto e herdou o bot. A URA numerada
        # ("Tudo está correto?") não aparece desde 26/12/2025.
        {"step": "confirmar_solicitacao", "anchor": r"como voc[êe] quer prosseguir",
         "reply": "Confirmar solicitação",
         "notes": "confirmação FINAL da URA em LISTA. Só alcançada em modo LIVE — no teste o freio cancela antes."},
        # POR ÚLTIMO, e a ordem É a regra (mesma lição do noop da família Allianz).
        #
        # 📊 "Está correto?\nBotão 1: Sim\nBotão 2: Não" — 13 ocorrências, a tela
        # de MAIOR frequência da Azul, e nenhum passo casava. Ela confirma o
        # geocode do endereço QUE NÓS digitamos (a mensagem anterior é sempre
        # "Localizei o endereço ...").
        #
        # A âncora é genérica de propósito — a URA não repete o endereço na
        # pergunta —, e por isso ela tem de ser consultada DEPOIS de
        # `telefone_correto` ("O número está correto?" → "1") e de
        # `confirmar_tudo` ("Tudo está correto?" → "1"): as duas também contêm
        # "está correto?" e as duas são menus NUMERADOS. Responder "Sim" a um
        # menu numerado é resposta inválida; responder "1" a esta lista de
        # botões também. `match_ura_step` devolve o PRIMEIRO que casa.
        # 🔴 ESTA ÂNCORA ROUBAVA A TELA DO TELEFONE — 22/08/2026.
        #    📊 `est[áa] correto\s*\?` casa **7** telas: 6 do endereço e
        #       **"O número está correto? {TELEFONE} *1* - Sim *2* - Não"**.
        #       Responder "Sim" ali confirma um telefone que ninguém conferiu —
        #       e é para esse número que o prestador liga quando não acha a casa.
        #    🔴 CONTROLE: com `^`, casa exatamente 6. `match_ura_step` compila
        #       com IGNORECASE|DOTALL e **sem** MULTILINE, então `^` é o início
        #       da mensagem inteira — que é onde a tela do endereço começa e a
        #       do telefone não.
        {"step": "numero_correto", "anchor": r"^o n[úu]mero est[áa] correto", "reply": "1",
         "notes": "📊 1 tela / 1 sessão. Vem ANTES de `endereco_correto` de propósito."},
        {"step": "endereco_correto", "anchor": r"^est[áa] correto\s*\?", "reply": "Sim",
         "notes": "confirma o geocode do endereço que NÓS digitamos (botões Sim/Não). "
                  "Passo GENÉRICO — precisa ficar depois dos específicos"},
    ],
    finalize_anchors=[
        # 📊 O freio REAL de 2026: a tela em lista (8 ocorrências, a última em
        # 28/07/2026). Antes desta linha a Azul não freava em NADA: o freio
        # declarado era `tudo está correto`, que não aparece desde 26/12/2025.
        r"como voc[êe] quer prosseguir",
        r"tudo est[áa] correto", r"posso confirmar", r"confirmar o agendamento",
    ],
)
# 🔴 O MENU DA AZUL MIGROU EM 07/04/2026, E O MAPA FICOU NO BOT ANTIGO.
#
# 📊 As duas variantes NÃO competem — elas se sucederam, e o corte é o MESMO dia
#    em TRÊS telas independentes (o que prova migração de bot, não ambiguidade):
#
#      "O que você precisa?" NUMERADA (1-8)   3 msgs · 17/09/2025 a 26/12/2025
#      "O que você precisa?" LISTA            8 msgs · 07/04/2026 a 28/07/2026
#
# 📊 E na variante VIVA (8 de 11 sessões) as opções são:
#      Guincho (reboque) · Bateria · Chaveiro para veículo · Técnico · Táxi
#    🔴 NÃO EXISTE "Troca de pneu" e NÃO EXISTE "vidro".
#
#    · `pneu` mandava "3" numa lista de RÓTULOS — rejeitado. Onde o pneu entra
#      em 2026 **não está estabelecido** (candidato: "Técnico", zero evidência).
#    · `vidros` mandava "5" — tecla morta desde 26/12/2025. Em 2026 vidro está
#      no menu RAIZ ("Vidros e faróis", 23 msgs / 16 sessões), não neste.
#
# 🔴 Sem rótulo observado, o correto é NÃO declarar a tecla: `subservice_supported`
#    devolve False e o caso vai a handoff. É a regra que `_ativar_vidros` já
#    escreve — "inventar rótulo de menu é o defeito que manda o segurado para a
#    opção errada" — aplicada aqui.
AZUL_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    "guincho": "Guincho (reboque)", "bateria": "Bateria",
    "chaveiro": "Chaveiro para veículo",
    # 🔴 `pneu` NÃO entra: nenhum rótulo dele existe no menu vivo.
}
# O CANCELAMENTO PRECISA SER ACEITÁVEL PELA TELA QUE ESTÁ NA FRENTE.
#
# Era "4", de "*4* - Sair e não agendar" do RESUMO numerado. 📊 Essa tela teve 2
# ocorrências e a última foi em 26/12/2025. A tela viva é LISTA, e nela a opção
# se chama "Sair e não agendar" — dígito é rejeitado ("Não entendi sua resposta.
# Selecione o botão abaixo", igual à Porto, que é o mesmo bot).
#
# Freio que dispara e manda uma resposta rejeitada não cancela nada: a sessão
# fica marcada `test_aborted` do nosso lado e a URA continua parada na tela de
# confirmação do lado da seguradora.
AZUL_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Sair e não agendar"

# --- BRADESCO (bot Europ; PLACA primeiro; fluxo REAL 05/01/2026) ------------------
BRADESCO_AUTO_WHATSAPP_V1 = _auto_playbook(
    "bradesco", "bradesco_assistencia_24h",
    ura_steps=[
        {"step": "menu_inicial", "anchor": r"voc[êe] quer assist[êe]ncia para", "reply": "Veículo",
         "notes": "Botão 1: Veículo / Botão 2: Residência (responder o rótulo)"},
        {"step": "informar_placa", "anchor": r"informa a \*?placa do ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"], "notes": "sem espaço/traço (formato estrito)"},
        {"step": "cpf_fallback", "anchor": r"digite somente os n[úu]meros do \*?cpf\*? ou \*?cnpj\*?", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"],
         "notes": "fallback quando a placa não é localizada"},
        {"step": "confirmar_veiculo", "anchor": r"podemos seguir o atendimento para este ve[íi]culo", "reply": "Sim",
        "constante_justificada": (
            "📊 A tela ECOA o veículo que a própria URA encontrou pela placa que NÓS enviamos. Confirmar é confirmar o que mandamos. ⚠️ Quando há MAIS DE UM veículo na apólice a tela é outra, e ali o passo é `escolher_veiculo`, com `dynamic: vehicle_by_plate`."),
         "notes": "URA mostra placa+modelo achados"},
        {"step": "problema", "anchor": r"qual o problema com o seu carro", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "1-Pane(bateria/motor) 2-Acidente 3-Pneus 4-Chave 5-Combustível — o serviço deriva do problema"},
        {"step": "pane_detalhe_guincho", "anchor": r"me conta o que aconteceu:", "reply": "2",
        "constante_justificada": (
            "📊 2-O veículo estava andando e parou de funcionar. Tecla do GUINCHO, com `only_subservices: [guincho]`. As duas juntas são a marca que distingue guincho de bateria no bradesco."),
         "only_subservices": ["guincho"],
         "notes": "guincho: 2-andando e parou (leva ao reboque)"},
        {"step": "pane_detalhe_bateria", "anchor": r"me conta o que aconteceu:", "reply": "1",
        "constante_justificada": (
            "📊 1-O veículo estava estacionado e não liga. É a tecla do BATERIA, e o passo é `only_subservices: [bateria]` — quem separa as duas rotas nesta tela é o subserviço, não o acaso."),
         "only_subservices": ["bateria"],
         "notes": "bateria: 1-estacionado e não liga (leva ao técnico/bateria)"},
        {"step": "hibrido_eletrico", "anchor": r"h[íi]brido/?el[ée]trico", "reply": "Não",
         "notes": "default Não; caso elétrico, adaptativo assume"},
        {"step": "garagem_subsolo", "anchor": r"garagem subsolo", "reply": "Não",
         "notes": "default Não; subsolo real → adaptativo"},
        {"step": "necessidades_especiais", "anchor": r"necessidades especiais ou mobilidade reduzida", "reply": "Não",
         "notes": "default Não; se houver no caso, adaptativo assume"},
        {"step": "quando", "anchor": r"envie a assist[êe]ncia agora ou prefere agendar", "reply": "Enviar agora",
        "constante_justificada": (
            "📊 'Agora' x 'Agendar'. O corredor só é acionado quando a corretora abriu um caso de assistência — que é, por definição, agora. ⚠️ Se um dia existir rota de AGENDAMENTO, esta constante vira slot."),
         "notes": "passo de COLETA no MEIO do fluxo (era FALSO freio) — urgência é o default"},
        {"step": "via_local_rodovia", "anchor": r"\*?via local\*? ou \*?rodovia", "reply": "Via local",
         "notes": "default via local; rodovia real → adaptativo (orientação de concessionária)"},
        {"step": "levar_oficina", "anchor": r"quer levar o ve[íi]culo at[ée] uma oficina", "reply": "Sim",
         "notes": "guincho com destino conhecido"},
        {"step": "oficinas_referenciadas", "anchor": r"op[çc][õo]es de oficinas referenciadas", "reply": "Não quero",
         "notes": "v1: destino do caso; oferecer as referenciadas ao cliente é evolução da Faixa 6"},
        {"step": "destino_rodovia", "anchor": r"pra onde voc[êe] quer levar seu ve[íi]culo, se encontra em uma \*?rodovia", "reply": "Nao",
         "notes": "destino em rodovia? default não"},
        # 🔴 ESTE PASSO NUNCA ERA ALCANÇADO — o freio casava a MESMA frase e
        #    cancelava em cima dele. Com o freio movido para o resumo final,
        #    ele volta a ser o que sempre foi: a confirmação do ENDEREÇO.
        {"step": "confirmar_abertura",
         "anchor": r"posso confirmar a abertura da assist[êe]ncia para este local",
         "reply": "Sim",
         "notes": "📊 3 sessões, turnos 20/28, 24/33 e 22/32. É confirmação de LOCAL: "
                  "a URA ainda pede agendamento, resumo e confirmação depois dela."},
        {"step": "tecnico_confirma", "anchor": r"resolver com a assist[êe]ncia de um t[ée]cnico",
         "reply": "Sim", "only_subservices": ["bateria"],
         "notes": "📊 1 sessão, turno 10/15. É o desfecho da tecla '1 - estacionado e não "
                  "liga': a URA decide TÉCNICO, não reboque. 🔴 Esta tela também disparava "
                  "o freio (`posso confirmar`), matando a rota bateria no meio."},
    ],
    finalize_anchors=[
        # ==================================================================
        # 🔴 O FREIO DISPARAVA 7 A 11 TURNOS CEDO DEMAIS — medido 22/08/2026
        # ==================================================================
        #
        # 📊 Rodando os `finalize_anchors` contra as 6 sessões, marcando o turno:
        #
        #   72af1ae1  turno 20/28  [posso confirmar a abertura]  ← a tela do ENDEREÇO
        #   0d5284f3  turno 24/33  [posso confirmar a abertura]  ← idem
        #   bc2cfead  turno 22/32  [posso confirmar a abertura]  ← idem
        #   2c05415b  turno 10/15  [posso confirmar]             ← a tela do TÉCNICO
        #   72af1ae1  turno 25/28  [posso confirmar a abertura]  ← ESTE é o freio
        #   0d5284f3  turno 31/33  [posso confirmar]             ← ESTE é o freio
        #   bc2cfead  turno 29/32  [posso confirmar]             ← ESTE é o freio
        #   72af1ae1  turno 28/28  [as informações estão corretas] ← REENTRADA
        #
        # 🔴 "Posso confirmar a abertura da assistência **PARA ESTE LOCAL**?" é
        #    confirmação de ENDEREÇO, não o resumo final. Em 3 de 4 sessões
        #    longas o freio cancelava 7 a 11 turnos antes de o serviço existir.
        #    E `as informações estão corretas` pegava a tela de REENTRADA
        #    ("Vi que você já identificou o veículo"), que também não é freio.
        #
        # ⚠️ É a MESMA família de defeito que o comentário antigo já corrigira
        #    uma vez ("'enviar agora ou prefere agendar' é COLETA, não freio!"),
        #    reaparecida numa tela vizinha. Freio largo demais não trava por
        #    excesso de zelo: cancela o trabalho antes de ele acontecer.
        #
        # 🔴 CONTROLE, os três, medidos:
        #    (a) as 3 telas de resumo final casam?  -> 3/3 ✅
        #    (b) casa a tela do ENDEREÇO?           -> 0 ✅  (antes: 3)
        #    (c) casa a tela de REENTRADA?          -> 0 ✅  (antes: 1)
        r"confira as informa[çc][õo]es que voc[êe] me forneceu",
        r"posso confirmar o agendamento da assist[êe]ncia",
        r"s[óo] vamos confirmar as informa[çc][õo]es",
    ],
)
BRADESCO_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "1", "bateria": "1", "pneu": "3", "chaveiro": "4"}
BRADESCO_AUTO_WHATSAPP_V1["finalize_abort_reply"] = "Não"
# Placa não localizada 2x → URA manda para a plataforma Europ (sem atendimento
# neste canal): vira handoff com a orientação no dossiê.
BRADESCO_AUTO_WHATSAPP_V1["handoff_triggers"] = BRADESCO_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    r"n[ãa]o podemos seguir com a sua solicita[çc][ãa]o",
]

# --- MAPFRE (exige DATA DE NASCIMENTO do titular; transfere cedo p/ humano) ------
MAPFRE_AUTO_WHATSAPP_V1 = _auto_playbook(
    "mapfre", "mapfre_assistencia_24h",
    ura_steps=[
        {"step": "pedir_cpf", "anchor": r"informe o \*?cpf\*? ou \*?cnpj do titular", "reply": "{titular_cpf}",
         "requires": ["titular_cpf"]},
        {"step": "nascimento", "anchor": r"data de nascimento da pessoa titular", "reply": "{titular_nascimento}",
         "requires": ["titular_nascimento"],
         "notes": "Mapfre valida identidade com dt. nascimento — coletar ANTES de acionar"},
        {"step": "menu_seguro", "anchor": r"sobre qual \*?seguro\*? voc[êe] quer falar", "reply": "Carro e moto"},
        {"step": "informar_placa", "anchor": r"informe o n[úu]mero da \*?placa do seu ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"]},
    ],
    finalize_anchors=[r"podemos confirmar", r"posso confirmar", r"deseja confirmar"],
)
MAPFRE_AUTO_WHATSAPP_V1["subservice_menu_map"] = {"guincho": "Assistência 24H", "bateria": "Assistência 24H", "pneu": "Assistência 24H", "chaveiro": "Assistência 24H"}
# Mapfre exige nascimento em TODOS os subserviços auto. O `**v` preserva as
# outras chaves do subserviço (outcome, tipo_servico_opcao): reconstruir só com
# `required_slots` apagava em silêncio tudo o mais que fosse declarado.
MAPFRE_AUTO_WHATSAPP_V1["subservices"] = {
    k: {**v, "required_slots": list(v["required_slots"]) + ["titular_nascimento"]}
    for k, v in _AUTO_SUBSERVICES.items()
}

# --- ZURICH (fluxo REAL 23/02/2026: listas por rótulo no topo, menus NUMERADOS
# no miolo, árvore de diagnóstico de pane, confirmação explícita no final) --------
ZURICH_AUTO_WHATSAPP_V1 = _auto_playbook(
    "zurich", "zurich_assistencia_24h",
    ura_steps=[
        {"step": "menu_assunto", "anchor": r"para qual dos assuntos voc[êe] precisa", "reply": "Carro e moto"},
        {"step": "menu_servicos", "anchor": r"escolha um dos servi[çc]os para continuar", "reply": "Assistência 24h"},
        {"step": "acionar_assistencia", "anchor": r"acionar a assist[êe]ncia 24h\*? ou \*?acionar o seguro", "reply": "Acionar assistência 24h",
         "notes": "colisão/roubo é SINISTRO (handoff), não assistência"},
        # VIDROS na Zurich é ITEM DE LISTA e é INFORMATIVO — DESFECHO = encaminha.
        # 📊 URA real 03/08/2026: "Você deseja acionar qual serviço? Acionar
        # seguro / Assistência {VALOR} / Assistência a vidros / Voltar ao menu".
        # Só o corredor de VIDROS responde este menu por rótulo: o rótulo dos
        # outros serviços vem com um VALOR variável da apólice, e adivinhá-lo
        # seria clicar na tecla errada. Para guincho/bateria/pneu/chaveiro este
        # passo não existe e quem decide continua sendo o adaptativo.
        {"step": "menu_acionar_servico_vidros", "anchor": r"deseja acionar qual servi[çc]o",
         "reply": "{servico_texto}", "requires": ["servico_texto"],
         "only_subservices": ["vidros"],
         "notes": "responder o rótulo 'Assistência a vidros' (vem de subservice_menu_map)"},
        # 📊 "*Assistência a vidros*: encontre informações sobre como pedir o
        # reparo ou a troca de vidros, para-brisa, faróis e retrovi[sores]" —
        # a Zurich ORIENTA; não abre chamado neste fluxo.
        # 🔴 O CARDÁPIO NÃO É A ESCOLHA — e este passo tomava um pelo outro.
        #
        # 📊 A âncora antiga (`assistência a vidros: encontre informações`) casava
        #    **8 mensagens em 7 das 15 sessões** do acervo, e as 8 eram a MESMA
        #    tela: o cardápio que a URA manda na 2ª mensagem depois de "Carro e
        #    moto" — ANTES do CPF, da placa, de escolher qualquer coisa:
        #
        #      "Aqui você pode de forma rápida e fácil:
        #       • *Assistência 24h*: solicite serviços de emergência…
        #       • *Assistência a vidros*: encontre informações sobre como pedir o
        #         reparo ou a troca de vidros, para-brisa, faróis…
        #       • *Sinistro*: …  • *Carro reserva*: …"
        #
        # 🔴 Com `outcome=OUTCOME_ENCAMINHA`, um caso de vidros na zurich
        #    **encerrava ali como `resolvido_por_encaminhamento`**, entregando ao
        #    segurado a legenda do menu como se fosse a resposta. A tela chega em
        #    7 de 15 sessões, sempre no começo: o encerramento era garantido.
        #
        # ⚠️ A tela de ORIENTAÇÃO de vidros — a que a URA manda para quem *escolhe*
        #    vidros — tem ZERO ocorrências no acervo: ninguém nunca escolheu. A
        #    âncora foi escrita a partir do cardápio, tomando a legenda pela
        #    resposta. A nova exige a marca que só a orientação tem (`acesse`,
        #    `clique`, `link`) e por isso fica DESLIGADA até haver fonte — o que é
        #    o estado honesto: handoff, e não um encerramento falso.
        {"step": "cardapio_carro_e_moto",
         "anchor": r"aqui voc[êe] pode de forma r[áa]pida e f[áa]cil",
         "reply": "", "noop": True,
         "notes": "📊 11 msgs · 9 de 15 sessões. CARDÁPIO, não escolha. A escolha é a "
                  "tela seguinte (Agora escolha um dos serviços), que tem `menu_servicos`. "
                  "🔴 PRECEDE `vidros_orientacao` de propósito: `match_ura_step` devolve "
                  "o PRIMEIRO que casa, e era o de vidros que a pegava."},
        {"step": "vidros_orientacao",
         "anchor": (r"acionar a assist[êe]ncia para vidros|"
                    r"assist[êe]ncia a vidros[\s\S]{0,40}(?:acesse|clique|link)"),
         "reply": "", "noop": True, "referral": True, "outcome": OUTCOME_ENCAMINHA,
         "notes": "🔴 IDENTIFICADA, NÃO ESTABELECIDA: 0 telas no acervo. A âncora exige "
                  "acesse|clique|link, que o cardápio não tem — é o que impede a volta "
                  "do defeito. Sem fonte, o caso de vidros vai a handoff, e isso é o certo."},
        {"step": "pedir_cpf", "anchor": r"qual o seu \*?cpf/?cnpj", "reply": "{titular_cpf}", "requires": ["titular_cpf"]},
        {"step": "pedir_placa", "anchor": r"qual a \*?placa do ve[íi]culo", "reply": "{veiculo_placa}",
         "requires": ["veiculo_placa"]},
        {"step": "confirmar_veiculo", "anchor": r"esse [ée] o ve[íi]culo que precisa de assist[êe]ncia", "reply": "1",
        "constante_justificada": (
            "📊 A tela ECOA o veículo que a própria URA encontrou pela placa que NÓS enviamos. Confirmar é confirmar o que mandamos. ⚠️ Quando há MAIS DE UM veículo na apólice a tela é outra, e ali o passo é `escolher_veiculo`, com `dynamic: vehicle_by_plate`."),
         "notes": "1-Sim (veículo achado pela placa do caso)"},
        {"step": "o_que_aconteceu", "anchor": r"me conte o que aconteceu", "reply": "{servico_opcao}",
         "requires": ["servico_opcao"],
         "notes": "menu numerado: 1-combustível 2-pneu 3-chave 4-panes 5-sinistro 6-terceiros; a árvore de diagnóstico ('o que houve?', câmbio etc.) fica com o adaptativo"},
        {"step": "rodovia", "anchor": r"est[áa] em estrada/?rodovia", "reply": "2",
         "notes": "1-Sim 2-Não; default Não, rodovia real → adaptativo"},
        {"step": "garagem", "anchor": r"garagem subsolo ou elevada", "reply": "2",
         "notes": "1-Sim 2-Não; default Não"},
        {"step": "endereco_livre", "anchor": r"compartilhe sua localiza[çc][ãa]o fixa ou me diga o endere[çc]o",
         "reply": "{local_atual}", "requires": ["local_atual"],
         # 🔴 19/08/2026: sem este filtro, um caso completo de VIDROS ficava
         # preso pedindo `local_atual` — 📊 medido:
         # `missing_slots_for_subservice(zurich, "vidros", caso_completo)`
         # devolvia `['servico_texto', 'local_atual']`.
         #
         # Vidros não pede o local do veículo porque o reparo é agendado numa
         # oficina, e por isso `local_atual` não está no `required_slots` dela.
         # Mas o gate recolhe `requires` de TODO passo sem filtro, então este
         # passo cobrava de todo mundo. Mesma classe do defeito de
         # eletrodoméstico no residencial da Allianz, achado no mesmo dia.
         "only_subservices": ["guincho", "pneu", "bateria", "chaveiro"],
         "notes": "aceita endereço em texto livre (Ex: Rua Sergipe, 1440 - Belo Horizonte)"},
        {"step": "endereco_detalhado", "anchor": r"digitar os dados do endere[çc]o de forma mais detalhada", "reply": "1",
        "constante_justificada": (
            "📊 Digitar detalhadamente x compartilhar localização. Mesma razão: o corredor não manda pin."),
         "notes": "fallback quando a localização/endereço não geocodifica; CEP/rua/nº pelo adaptativo"},
        {"step": "ref_opcional", "anchor": r"algum ponto de refer[êe]ncia que gostaria de informar", "reply": "2",
         "notes": "1-Sim 2-Não (menu NUMERADO — texto livre é rejeitado aqui)"},
        {"step": "endereco_correto", "anchor": r"os dados est[ãa]o corretos", "reply": "1",
         "notes": "confirma o resumo do ENDEREÇO (meio do fluxo — não é o freio)"},
        {"step": "tipo_assistencia", "anchor": r"qual o tipo de assist[êe]ncia voc[êe] gostaria", "reply": "1",
        "constante_justificada": (
            "📊 1-Imediata 2-Agendada. Mesma razão do `quando`: o corredor só roda para acionamento aberto agora."),
         "notes": "1-Imediata 2-Agendada"},
        {"step": "destino_livre", "anchor": r"para onde devemos levar seu ve[íi]culo", "reply": "{local_destino}",
         "notes": "guincho: destino em texto livre"},
        {"step": "telefone_e_esse", "anchor": r"seu telefone de contato para a assist[êe]ncia [ée]", "reply": "2",
         "notes": "2-Não → informamos o telefone do caso no passo seguinte (nunca herdar contato errado)"},
        {"step": "telefone", "anchor": r"confirmar? pra n[óo]s o seu \*?n[úu]mero de telefone", "reply": "{telefone_contato}",
         "requires": ["telefone_contato"]},
        {"step": "confirmar_solicitacao", "anchor": r"podemos confirmar a solicita[çc][ãa]o", "reply": "1",
         "notes": "confirmação FINAL. Só alcançada em modo LIVE — no teste o freio cancela antes."},
    ],
    finalize_anchors=[r"podemos confirmar a solicita[çc][ãa]o", r"posso confirmar", r"deseja confirmar"],
)
ZURICH_AUTO_WHATSAPP_V1["subservice_menu_map"] = {
    # Menu 2026 'me conte o que aconteceu' é NUMERADO: 1-combustível 2-pneu
    # 3-chave 4-panes 5-sinistro 6-reboque p/ terceiros. Bateria = pane (4) e o
    # detalhe (Problema de Bateria) o adaptativo escolhe na árvore de diagnóstico.
    "guincho": "4", "bateria": "4", "pneu": "2", "chaveiro": "3",
}
ZURICH_AUTO_WHATSAPP_V1["finalize_abort_reply"] = ""  # sem opção de sair no resumo: silêncio (URA encerra sozinha)


# ===========================================================================
# VIDROS — ligado em TRÊS seguradoras, e desligado nas outras sete
# ===========================================================================
# 📊 `ura_maps` status='observed', banco de produção, 03/08/2026.
#
#   azul .... TECLA numerada: "*5* - Conserto ou troca de vidro, retrovi[sor]"
#             → desfecho ABRE: segue o fluxo normal até o protocolo.
#   porto ... item de LISTA: "Conserto de vidro (Inclui retrovisor, farol ou
#             lanterna)" → e o fluxo TERMINA num formulário → desfecho ENCAMINHA.
#   zurich .. item de LISTA: "Assistência a vidros" → texto informativo sobre
#             como pedir o reparo → desfecho ENCAMINHA.
#
# 📊 SEM evidência de vidro no menu de assistência: allianz, tokio, mapfre,
# yelum, hdi, alfa. (bradesco também não tem.) Nessas, `vidros` NÃO é declarado:
# `subservice_supported()` devolve False, `missing_slots_for_subservice()`
# devolve ["subservico_invalido"] e o caso vira handoff humano. É de propósito.
# Ligar vidros nas dez "porque o produto sabe falar de vidro" faria o corredor
# apertar uma tecla que não existe na tela daquela seguradora.
_VIDROS_REFERRAL_PORTO = {
    "kind": "formulario",
    "closes_as": "resolvido_por_encaminhamento",
    "link_capture": "tracking_link",  # o link chega numa mensagem sozinha
    "client_message": (
        "A Porto trata vidro, retrovisor, farol e lanterna por FORMULÁRIO de sinistro de vidros — "
        "não é chamado aberto pelo WhatsApp da assistência. Encaminhe ao segurado o link que a "
        "seguradora enviou NESTA conversa (nunca digite um endereço de memória) e repasse o que a "
        "própria URA diz: este acionamento para vidros não afeta a classe de bônus."
    ),
}
_VIDROS_REFERRAL_ZURICH = {
    "kind": "orientacao",
    "closes_as": "resolvido_por_encaminhamento",
    "link_capture": "tracking_link",
    "client_message": (
        "A Zurich responde vidros com ORIENTAÇÃO: onde encontrar como pedir o reparo ou a troca de "
        "vidros, para-brisa, faróis e retrovisores. Repasse ao segurado exatamente o que a seguradora "
        "enviou nesta conversa — sem completar com prazo, valor ou franquia que ela não disse."
    ),
}
# 🔴 DESLIGADO EM 22/08/2026: `menu_value="5"` aponta para uma tecla que morreu
#    com a URA numerada em 26/12/2025. 📊 Na variante viva não há opção de vidro
#    neste menu — ele está no menu RAIZ ("Vidros e faróis"), cujo fluxo NÃO foi
#    observado. Ligar `vidros` com a tecla velha manda "5" e a URA rejeita.
#    Com a chamada removida, `subservice_supported(azul, "vidros")` devolve
#    False e o caso vai a handoff — que é o estado honesto até haver captura.
# _ativar_vidros(AZUL_AUTO_WHATSAPP_V1, menu_value="5", outcome=OUTCOME_ABRE)
_ativar_vidros(PORTO_AUTO_WHATSAPP_V1, menu_value="Conserto de vidro",
               outcome=OUTCOME_ENCAMINHA, referral=_VIDROS_REFERRAL_PORTO)
_ativar_vidros(ZURICH_AUTO_WHATSAPP_V1, menu_value="Assistência a vidros",
               outcome=OUTCOME_ENCAMINHA, referral=_VIDROS_REFERRAL_ZURICH)


# ===========================================================================
# SPEC-063: RESIDENCIAL fora da Allianz — HDI e Porto
# ===========================================================================
# Até 03/08/2026 havia UM corredor residencial (Allianz) e dez de auto. Estes
# dois nascem do que foi OBSERVADO, e só dele: onde a evidência acaba, o passo
# não existe e o motor cai no adaptativo guardado / handoff, como já faz hoje.
#
# Uma escolha explícita: onde o corredor de auto da MESMA seguradora já tinha
# uma âncora de identificação (CPF, menu raiz), ela é REUSADA e marcada nas
# `notes`. É a mesma URA, o mesmo bot e a mesma porta de entrada — reusar não é
# inventar. O que NÃO é reusado é qualquer passo com cara de auto (placa, cor do
# veículo, rodovia, garagem): esses não têm equivalente residencial observado.

_RESID_HUMAN_PHASE_GUIDANCE = (
    "Voce conduz, EM NOME DA CORRETORA, um acionamento de assistencia RESIDENCIAL no WhatsApp da "
    "seguradora. Pode ser a URA (menu numerado ou botoes) ou um atendente humano. Responda menus "
    "escolhendo a opcao coerente com o subservico/dados do caso; responda pedidos de dado com o valor "
    "exato do caso (CPF, endereco da apolice, telefone). O endereco e o DA APOLICE — nao invente, e "
    "nao use endereco de outro caso. Se a seguradora for CONFIRMAR/ABRIR o servico, NAO confirme: o "
    "passo final exige aprovacao da corretora. Se a seguradora disser que a apolice nao tem cobertura "
    "residencial ou que acabaram as utilizacoes, NAO insista: registre e devolva ao humano. Use "
    "SOMENTE dados do caso. Se nao der pra deduzir, responda exatamente: NAO_SEI."
)

# Resumo estruturado ao ESPECIALISTA humano da assistência (residencial).
# Só usa chaves de `_optional_keys()` — chave fora dali derruba o template
# inteiro para o texto genérico de auto.
_RESID_OPENING_TEMPLATE = (
    "Ola, aqui e a corretora. Preciso acionar {subservice_label} para a residencia do nosso segurado.\n"
    "Titular: {titular_nome} (CPF {titular_cpf})\n"
    "Endereco: o da apolice, numero {endereco_numero}\n"
    "Problema: {problema_descricao}\n"
    "Telefone de contato: {telefone_contato}\n"
    "Periodo preferido: {periodo_preferido}"
)

_RESID_HANDOFF_TRIGGERS = [
    r"sinistro", r"n[ãa]o localizamos", r"cpf.*inv[áa]lido", r"n[ãa]o foi poss[íi]vel",
    r"sem cobertura", r"n[ãa]o (?:tem|possui) cobertura",
]

# Os dados que cada TRABALHO exige — não os que cada seguradora exige.
# O eletricista pergunta de fumaça, o encanador pergunta do registro e o
# eletrodoméstico pergunta da marca, seja na Allianz ou na HDI. Guardrail que
# existe só num corredor não é guardrail: é coincidência.
_RESID_SLOTS_BASE = ["titular_cpf", "telefone_contato", "problema_descricao"]
_RESID_SLOTS_POR_TRABALHO = {
    "encanador": ["vazamento_local", "agua_escorrendo", "risco_confirmado_registro_fechado"],
    "eletricista": ["risco_confirmado_sem_fumaca"],
    "eletrodomesticos": ["aparelho_marca_modelo", "aparelho_idade"],
    "chaveiro": [],
    "desentupimento": [],
}


def _resid_slots(trabalho: str) -> List[str]:
    # 🔴 `pessoa_no_local` E OBRIGATORIO NO RESIDENCIAL -- 22/08/2026.
    #
    # 📊 O conferidor de respostas achou 5 passos em 3 corredores
    #    (hdi, porto, yelum) exigindo o slot sem que nada o preenchesse. As
    #    telas, literais:
    #      "Por favor, informe o nome da pessoa que estara na residencia para
    #       receber o tecnico."
    #      "Nesse caso, qual e o nome de quem estara na residencia? Lembrando
    #       que e necessario ter mais de 18 anos de idade para acompanhar."
    #
    # ⚠️ A propria URA diz por que o dado importa: sem alguem maior de 18 no
    #    local, o prestador aguarda 15 minutos e vai embora. O corredor sabia a
    #    regra (esta em `client_instructions`) e nao coletava o nome.
    return (list(_RESID_SLOTS_BASE)
            + list(_RESID_SLOTS_POR_TRABALHO.get(trabalho) or [])
            + ["pessoa_no_local"])


# --- HDI residencial (📊 o corredor residencial mais bem observado do acervo) ---
# Mesmo bot white-label "Assistência 24 horas" do corredor de auto da HDI/Yelum:
# botões por rótulo, timeout de 12 min, protocolo no mesmo formato.
#
# NÃO há passo de endereço aqui, e isso é evidência, não esquecimento: a URA
# identifica a apólice pelo CPF e trabalha com o endereço dela. Se aparecer um
# passo pedindo endereço, ele vira `pending` e o humano assume — melhor que um
# slot obrigatório que ninguém usa, cobrado do cliente por precaução.
HDI_RESIDENCIAL_WHATSAPP_V1: Dict[str, Any] = {
    "playbook_id": "hdi-residencial-whatsapp",
    "version": 1,
    "insurer_key": "hdi",
    "line_kind": "residencial",
    "channel": "whatsapp",
    "insurer_contact_ref": "hdi_assistencia_24h",
    "description": ("Assistência 24h RESIDENCIAL HDI via WhatsApp "
                    "(encanador/desentupimento/eletricista/chaveiro/eletrodoméstico)."),
    "ura_steps": [
        {"step": "identificacao_dado",
         "anchor": (r"informe \*?apenas um dos dados|informe \*?um dos dados abaixo|"
                    r"informe somente o \*?cpf ou cnpj\*? do t[íi]tular"),
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "âncora REUSADA do corredor de auto da MESMA URA — a identificação é a mesma "
                  "porta para os dois ramos"},
        {"step": "desambiguacao_veiculo_ou_residencial",
         "anchor": r"identifiquei em seu cadastro a placa",
         "reply": "Residencial",
         "notes": "📊 'Identifiquei em seu cadastro a placa {PLACA}. Deseja continuar com o "
                  "atendimento para o veículo ou atendimento residencial? Botão 1: Automóvel "
                  "Botão 2: Residencial'. O corredor de AUTO responde 'Automóvel' nesta MESMA "
                  "tela — é o passo que separa os dois ramos, e errar aqui atende o carro de "
                  "quem pediu encanador"},
        # 🔴 O MESMO MENU, DUAS REDAÇÕES — e a âncora só conhecia uma.
        #
        # 📊 04/08/2026, `observed_events` (hdi + yelum, mesmo bot white-label):
        #
        #   "Qual é o serviço que você precisa solicitar?"   hdi 7 · yelum 3
        #   "Qual o serviço que você precisa?"               hdi 7 · yelum 3
        #
        # A segunda perde o "é" E o "solicitar" — os dois pedaços que a âncora
        # literal exigia. `match_ura_step` devolvia NENHUM em metade das
        # entradas, no passo que ESCOLHE O TRABALHO. O corredor emudecia diante
        # da tela que ele existe para responder.
        #
        # O "é" e o "solicitar" viram opcionais — a mesma solução do
        # `_HDI_FAMILY_AGORA_OU_AGENDAR`, que já tinha três redações da mesma
        # pergunta. A âncora fica presa ao que não varia: "o serviço que você
        # precisa".
        {"step": "menu_servico_residencial",
         "anchor": r"qual (?:[ée] )?o servi[çc]o que voc[êe] precisa",
         "reply": "{tipo_servico_opcao}", "requires": ["tipo_servico_opcao"],
         "notes": "📊 lista real: Encanador (conserto de vazamentos como torneiras, sifões, etc) / "
                  "Desentupimento (desentupimento residencial) / Eletricista / Chaveiro / "
                  "Linha branca / Ar condicionado — responder o RÓTULO, que vem do subserviço"},
        {"step": "servico_ja_aberto",
         "anchor": r"localizamos o servi[çc]o de .{0,80}?deseja acompanhar",
         "reply": "Novo serviço",
         "notes": "📊 'Para esse CPF localizamos o serviço de *ENCANADOR*. Deseja acompanhar? "
                  "Botão 1: Acompanhar Botão 2: Novo serviço Botão 3: Voltar'. O corredor abre o "
                  "que o cliente pediu HOJE. Acompanhar chamado antigo é outro trabalho e quem "
                  "decide é o atendente"},
        {"step": "utilizacoes_restantes",
         "anchor": r"(?:tem somente|possui)\s+\d+\s+utiliza[çc][õo]es",
         "reply": "", "noop": True,
         "notes": "📊 'Segurada tem somente 2 utilizações de encanador nessa apólice' — informativo "
                  "sobre o LIMITE da apólice: registrar no dossiê e seguir, nunca responder"},
    ],
    "subservices": {
        "encanador": {"tipo_servico_opcao": "Encanador", "required_slots": _resid_slots("encanador")},
        "desentupimento": {"tipo_servico_opcao": "Desentupimento", "required_slots": _resid_slots("desentupimento")},
        "eletricista": {"tipo_servico_opcao": "Eletricista", "required_slots": _resid_slots("eletricista")},
        "chaveiro": {"tipo_servico_opcao": "Chaveiro", "required_slots": _resid_slots("chaveiro")},
        "eletrodomesticos": {"tipo_servico_opcao": "Eletrodoméstico", "required_slots": _resid_slots("eletrodomesticos")},
    },
    # O rótulo do menu vai em `tipo_servico_opcao` (e NÃO em `subservice_menu_map`)
    # porque é essa a chave que o motor injeta em linha residencial. Declarar nas
    # duas seria manter dois lugares dizendo a mesma coisa, para divergirem depois.
    "subservice_labels": {
        "encanador": "encanador", "desentupimento": "desentupimento",
        "eletricista": "eletricista", "chaveiro": "chaveiro",
        "eletrodomesticos": "reparo de eletrodomestico",
    },
    "opening_template": _RESID_OPENING_TEMPLATE,
    "human_phase_guidance": _RESID_HUMAN_PHASE_GUIDANCE,
    # Mesmo bot do corredor de auto da HDI → mesmo formato de protocolo/ETA.
    # (o prefixo `_AUTO_` do nome é de onde a âncora foi minerada, não do ramo.)
    "capture_anchors": dict(_AUTO_CAPTURE_ANCHORS),
    # Sem regras fixas ao cliente observadas nesta URA. A do maior de 18 anos e a
    # da senha de acesso são da Allianz — copiá-las para cá seria inventar.
    "client_instructions": [],
    "handoff_triggers": _RESID_HANDOFF_TRIGGERS + [
        # 📊 "Ela não possui mais utilizações de encanador": limite ESGOTADO.
        # Não há acionamento possível — insistir só queima o tempo do segurado.
        r"n[ãa]o possui mais utiliza[çc][õo]es",
        # 🔴 AQUI o gatilho FICA — e é uma diferença deliberada em relação ao
        # corredor de auto da mesma seguradora, que o perdeu em 03/08/2026.
        #
        # O canal de resposta existe e foi provado. Mas este playbook **não
        # declara `native_flows`**: nenhum formulário do residencial foi
        # capturado ainda. Sem schema não há o que responder, e a única saída
        # honesta é pausar com o dossiê.
        #
        # Quando um formulário residencial for observado e virar schema, este
        # gatilho sai — e não antes.
        r"formulario nativo",
    ],
    "finalize_anchors": [
        # ponto de não-retorno da família HDI/Yelum — o "para" é OPCIONAL: 📊 a
        # tela residencial da HDI diz "Você precisa do atendimento agora ou
        # prefere agendar" (sessão 26c0546f, 02/06/2026, encanador) e a âncora
        # literal antiga não disparava justamente aqui.
        _HDI_FAMILY_AGORA_OU_AGENDAR,
        r"podemos confirmar", r"posso confirmar", r"deseja confirmar",
    ],
    "finalize_abort_reply": "Sair",  # 'Digite Sair para encerrar'
    "unknown_step_policy": "pause_and_handoff",  # corredor novo: pausa antes de improvisar
    "coverage_guardrails": [
        "📊 'Ela não possui mais utilizações de encanador' — a apólice residencial tem LIMITE de "
        "utilizações POR SUBSERVIÇO. Esgotado, não existe acionamento: é handoff com o motivo "
        "escrito, e a corretora oferece o serviço particular se o cliente quiser.",
        "📊 'Segurada tem somente 2 utilizações de encanador nessa apólice' — quando a URA disser "
        "quantas restam, isso vai ao dossiê: é o dado que evita gastar a última utilização num "
        "problema pequeno.",
    ],
}

# --- PORTO residencial (a rota existe; os subserviços são genéricos) --------------
# 📊 A Porto expõe a ROTA ("Serviços para residência") e descreve o que ela cobre
# ("Assistência de elétrica, hidráulica e conserto de eletrodomésticos"), mas
# NENHUM submenu de escolha do subserviço foi observado. Por isso este corredor
# NÃO declara rótulo de menu por subserviço: ele chega até a rota residencial e,
# do submenu em diante, quem conduz é o adaptativo guardado / o humano.
# Declarar um rótulo aqui seria adivinhar a tecla.
PORTO_RESIDENCIAL_WHATSAPP_V1: Dict[str, Any] = {
    "playbook_id": "porto-residencial-whatsapp",
    "version": 1,
    "insurer_key": "porto",
    "line_kind": "residencial",
    "channel": "whatsapp",
    "insurer_contact_ref": "porto_assistencia_24h",
    "description": "Assistência RESIDENCIAL Porto via WhatsApp (elétrica/hidráulica/eletrodomésticos).",
    "ura_steps": [
        # 🔴 O LAÇO: ESTE PASSO RE-IDENTIFICAVA PARA SEMPRE — 22/08/2026.
        #
        # 📊 `menu_raiz` casa 13 vezes em 8 sessões do corpus residencial, e
        #    respondia "Informar outro CPF/CNPJ" **as 13**. O corredor de AUTO
        #    resolve o mesmo padrão com `reply_if_step_done` desde sempre; o
        #    residencial não tinha, e por isso nunca chegava à linha residencial.
        #
        # ⚠️ E os dois passos seguintes (`menu_tipo_atendimento`,
        #    `menu_como_ajudar_resid`) casam **ZERO** telas em 210 — eles são
        #    órfãos de USO, não só de texto: a URA nunca chega neles.
        #
        # A nota antiga dizia "o rótulo residencial da 2ª volta não foi
        # observado, e chutar manda o caso para a rota errada". Era verdade
        # quando foi escrita. 📊 Agora foi observado, 8 de 8 ocorrências:
        #
        #    "{NOME}, escolha a opção desejada:
        #     Seguro Auto | **Serviço para residência** | Serviços Particulares
        #     | Sinistro de terceiro | Contrate a Porto | Informar outro CPF/CNPJ"
        #
        # 🔴 "Serviço para residência" — **SINGULAR**, sem o "s" em Serviço.
        #    `menu_tipo_atendimento` responde "ServiçoS para residência", que
        #    não existe em nenhuma das 8 telas.
        # 🔴 A MESMA FRASE ABRE DUAS TELAS DIFERENTES — achado do conferidor de
        #    respostas em 22/08/2026, e o `menu_raiz` respondia a errada.
        #
        # 📊 "escolha a opção desejada" casa TAMBÉM as telas de serviço já aberto:
        #
        #   "Carlos, localizei o seguinte serviço realizado. Por favor, escolha a
        #    opção desejada.
        #      Falar sobre 1-{NUMERO}-Hidráulica, realizado em {DATA}
        #      Outro assunto"
        #
        # 🔴 Responder "Informar outro CPF/CNPJ" ali manda um rótulo que **não
        #    está entre as opções** — a URA rejeita e o turno se perde. E quem
        #    quer abrir um serviço NOVO precisa de "Outro assunto".
        #
        # ⚠️ Este passo vem ANTES do `menu_raiz`, e a âncora dele exige a marca
        #    que só a tela de serviço-aberto tem.
        {"step": "servico_ja_aberto_menu",
         "anchor": (r"localizei (?:o seguinte|os seguintes) servi[çc]os?"
                    r"[\s\S]{0,400}outro assunto"),
         "reply": "Outro assunto",
         "notes": "📊 4 telas / 4 sessões. 🔴 O corredor existe para ABRIR: 'Falar "
                  "sobre <serviço já feito>' é acompanhamento, que é outro trabalho."},
        {"step": "menu_raiz", "anchor": r"escolha a op[çc][ãa]o desejada",
         "reply": "Informar outro CPF/CNPJ",
         "reply_if_step_done": {"step": "pedir_cpf", "reply": "Serviço para residência"},
         "notes": "📊 13 msgs / 8 sessões. Na 1ª volta re-identifica (o CPF lembrado é o do "
                  "cliente ANTERIOR); depois do nosso CPF, entra na linha residencial pelo "
                  "rótulo medido — SINGULAR, 8 de 8 ocorrências. "
                  "⚠️ Vem DEPOIS de `servico_ja_aberto_menu`: a mesma frase abre as duas "
                  "telas, e só a de serviço-aberto tem 'Outro assunto'."},
        {"step": "pedir_cpf", "anchor": r"(?:informe|digite) o (?:seu )?\*?cpf ou cnpj\*?",
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "âncora REUSADA do corredor de auto da Porto (mesma porta de identificação)"},
        # 🔴 OS DOIS PASSOS QUE CASAVAM ZERO EM 210 TELAS — medidos 22/08/2026.
        #
        #   menu_raiz               msgs=13  ses=8
        #   pedir_cpf               msgs= 5  ses=5
        #   menu_tipo_atendimento   msgs= 0  ses=0   🔴
        #   menu_como_ajudar_resid  msgs= 0  ses=0   🔴
        #
        # "qual tipo de atendimento você precisa" e "como eu posso te ajudar? …
        # serviços para residência" não existem no corpus residencial da porto,
        # nem ampliando `.` para `[\s\S]`. A URA residencial nunca escreve
        # essas frases. Ficam como ALTERNATIVA do passo que casa a tela real —
        # não custam nada e cobrem a redação do corredor de auto, se ela vier.
        {"step": "menu_produto_residencia",
         "anchor": (r"(?:escolha|informe) a op[çc][ãa]o desejada[\s\S]{0,600}"
                    r"servi[çc]o para resid[êe]ncia|"
                    r"qual tipo de atendimento voc[êe] precisa|"
                    r"como eu posso te ajudar\?[\s\S]{0,300}servi[çc]os? para resid[êe]ncia"),
         "reply": "Serviço para residência",
         "notes": "📊 8 msgs / 8 sessões. 🔴 O rótulo é SINGULAR ('Serviço para residência') "
                  "em 8 de 8 telas. ⚠️ Vem DEPOIS de `menu_raiz` na lista: na 1ª volta quem "
                  "responde é o menu_raiz (re-identificando); este pega a 2ª, e a variante "
                  "'localizei o seu Seguro Auto e o seu Cartão' que traz a mesma linha."},
        {"step": "aguarde",
         "anchor": (r"aguarde um momento|que bom ter voc[êe] de volta|aguarde enquanto solicito|"
                    r"falta pouco para finalizarmos"),
         "reply": "", "noop": True,
         "notes": "noop REUSADO do corredor de auto: mensagens de espera não se respondem"},
    ],
    "subservices": {
        "eletricista": {"required_slots": _resid_slots("eletricista")},
        "encanador": {"required_slots": _resid_slots("encanador")},
        "eletrodomesticos": {"required_slots": _resid_slots("eletrodomesticos")},
    },
    # As palavras da Porto, para o resumo ao analista humano. As CHAVES são as
    # canônicas do produto (eletricista/encanador/eletrodomesticos): a Porto
    # chamar de "elétrica" e "hidráulica" não pode virar um segundo vocabulário
    # — `canonical_subservice` traduz 'eletrica'/'hidraulica' para cá.
    "subservice_labels": {
        "eletricista": "assistencia de eletrica",
        "encanador": "assistencia de hidraulica",
        "eletrodomesticos": "conserto de eletrodomestico",
    },
    "opening_template": _RESID_OPENING_TEMPLATE,
    "human_phase_guidance": _RESID_HUMAN_PHASE_GUIDANCE,
    "capture_anchors": dict(_AUTO_CAPTURE_ANCHORS),
    "client_instructions": [],
    "handoff_triggers": _RESID_HANDOFF_TRIGGERS + [
        # 📊 "Parece que as apólices no CNPJ informado não tem cobertura para
        # serviços residenciais. Nestes casos é possível realizar a assistência
        # de forma particular." Serviço PARTICULAR não é acionamento de apólice:
        # é conversa comercial com o cliente, e ela é de gente.
        r"n[ãa]o tem cobertura para servi[çc]os residenciais",
        r"assist[êe]ncia de forma particular",
    ],
    "finalize_anchors": [
        r"como voc[êe] quer prosseguir", r"posso confirmar sua solicita[çc][ãa]o",
        r"posso confirmar", r"deseja confirmar",
    ],
    "finalize_abort_reply": "Sair e não agendar",
    "unknown_step_policy": "pause_and_handoff",
    "coverage_guardrails": [
        "📊 'Parece que as apólices no CNPJ informado não tem cobertura para serviços residenciais. "
        "Nestes casos é possível realizar a assistência de forma particular.' — apólice sem cobertura "
        "residencial NÃO vira acionamento. Vira handoff, e a oferta de serviço particular é decisão "
        "comercial da corretora com o cliente.",
        "📊 Nenhum submenu de subserviço residencial foi observado na Porto: do 'Serviços para "
        "residência' em diante o corredor não tem tecla mapeada.",
    ],
}


# --- YELUM residencial -------------------------------------------------------
#
# 📊 04/08/2026, `observed_events` (banco de produção `dcajcvlzcjbmyapmklil`).
# A Yelum é o MESMO bot white-label "Assistência 24 horas" da HDI — e por isso a
# tentação era copiar `HDI_RESIDENCIAL_WHATSAPP_V1` e trocar o `insurer_key`.
# A medição desautorizou a cópia.
#
# O QUE A EVIDÊNCIA DIZ (query: `observed_events` por `insurer_key`)
# ------------------------------------------------------------------
#
#     sinal                                        yelum   hdi
#     eventos totais                                3.026  2.074
#     "Identifiquei ... a placa" (desambiguação)       23      8
#     menções a encanador                              44     28
#     menções a eletricista                            39     27
#     menções a chaveiro                               46     33
#     "serviço que você precisa"                        6     14
#     "utilizações"                                     0      4   <-- ZERO
#
# São 6 sessões residenciais completas da Yelum, três delas indo 100% pelo bot
# até o protocolo (8981006 · 9124710 · 9666474). É mais evidência do que a HDI
# tinha quando o corredor dela foi escrito.
#
# 🔴 SEIS ÂNCORAS DA FAMÍLIA NÃO CASAM COM O TEXTO DA YELUM
#
# Medido rodando cada regex contra a mensagem literal:
#
#     passo                âncora da família/HDI                    Yelum diz
#     identificacao        "informe somente o *CPF ou CNPJ* do      "informe o *CPF ou CNPJ*
#                           titular"                                 que deseja atendimento"
#     informar_nome        "informe o seu nome ou como..."          "Me informe seu *nome* ou como"
#     perfil               "em qual dessas opções você se           "escolha a opção que melhor
#                           enquadra"                                te representa"
#     confirma_endereco    "você confirma O endereço"               "Você confirma ESTE endereço?"
#     nome_pessoa_local    "qual é o nome da pessoa que está        "qual é o nome da pessoa
#                           no local"                                responsável por acompanhar
#                                                                    o técnico no local"
#     servico_ja_aberto    "localizamos o serviço de X"             "localizamos algumas
#                                                                    assistências"
#
# Copiar a HDI teria produzido um corredor que emudece em SEIS telas — inclusive
# na que pede o CPF. As âncoras abaixo são as da YELUM, e onde as duas famílias
# escrevem igual a âncora aceita as duas redações.
#
# 🔴 E O MENU TEM OUTRO RÓTULO: a Yelum chama eletrodoméstico de **"Linha
# branca"**. Responder "Eletrodoméstico" (o rótulo da HDI) aperta uma tecla que
# não existe nesta tela.
#
# O QUE ESTE CORREDOR **NÃO** DECLARA, E POR QUÊ
# ----------------------------------------------
# 📊 `utilizações`: ZERO ocorrências na Yelum (a HDI tem 4). O passo
# `utilizacoes_restantes`, o gatilho "não possui mais utilizações" e os dois
# `coverage_guardrails` de limite por apólice ficam de fora. O que cobre a
# lacuna não é uma lista: é `unknown_step_policy: pause_and_handoff` — tela
# desconhecida pausa o acionamento com o dossiê, antes de improvisar.
# **Destrava quando aparecer uma sessão da Yelum com o texto de limite.**
#
# 📊 "Esta residência possui complemento?" e os horários de entrada em
# condomínio: 1 sessão cada, e a resposta depende do caso. Um passo com
# `reply` chutado aqui aperta botão errado; sem passo, o corredor pausa.
#
# 📊 "Ar condicionado", "Dedetização" e "Linha marrom" aparecem no menu real, e
# NÃO existe subserviço canônico para eles no produto. Declarar rótulo sem
# subserviço criaria uma tecla sem trabalho do outro lado.

_YELUM_RESID_ABERTURA = (
    r"seja bem-?vindo ao atendimento digital|"
    r"vi que voc[êe] est[áa] precisando de uma assist[êe]ncia residencial|"
    r"dicas sobre como funciona o nosso atendimento|"
    r"aqui voc[êe] pode \*?acompanhar\*? todas as suas assist[êe]ncias"
)

YELUM_RESIDENCIAL_WHATSAPP_V1: Dict[str, Any] = {
    "playbook_id": "yelum-residencial-whatsapp",
    "version": 1,
    "insurer_key": "yelum",
    "line_kind": "residencial",
    "channel": "whatsapp",
    "insurer_contact_ref": "yelum_assistencia_24h",
    "description": ("Assistência 24h RESIDENCIAL Yelum via WhatsApp "
                    "(encanador/desentupimento/eletricista/chaveiro/linha branca)."),
    "ura_steps": [
        {"step": "abertura", "anchor": _YELUM_RESID_ABERTURA, "reply": "", "noop": True,
         "notes": "📊 'Olá, seja bem-vindo ao atendimento digital de *Assistência 24 horas* da "
                  "*Yelum Seguradora!*' (6 de 6 sessões) — saudação e dicas de uso não se respondem"},
        {"step": "menu_auto_ou_resid",
         "anchor": (r"assist[êe]ncia para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia|"
                    r"servi[çc]os de assist[êe]ncia para seu \*?autom[óo]vel\*? ou \*?resid[êe]ncia"),
         "reply": "🏠 Residência",
         "notes": "📊 'Você gostaria de solicitar serviços ou acompanhar serviços de assistência "
                  "para seu *automóvel* ou *residência*? Botão 1: 🚗 Automóvel Botão 2: 🏠 Residência' "
                  "(3 sessões; a variante sem 'solicitar' aparece 10x). O RÓTULO tem emoji — é ele "
                  "que a tela mostra, e é ele que se responde"},
        {"step": "desambiguacao_veiculo_ou_residencial",
         "anchor": r"identifiquei em seu cadastro a placa",
         "reply": "Residencial",
         "notes": "📊 23 ocorrências na Yelum (contra 8 na HDI) — é a tela mais observada dos dois "
                  "ramos. 'Identifiquei em seu cadastro a placa {PLACA}. Deseja continuar com o "
                  "atendimento para o veículo ou atendimento residencial? Botão 1: Automóvel "
                  "Botão 2: Residencial'. O corredor de AUTO da Yelum responde 'Automóvel' nesta "
                  "MESMA tela: errar aqui atende o carro de quem pediu encanador"},
        {"step": "identificacao_dado",
         "anchor": (r"informe somente o \*?cpf ou cnpj\*? do t[íi]tular|"
                    r"informe \*?apenas um dos dados|informe \*?um dos dados abaixo|"
                    r"informe o \*?cpf ou cnpj\*? que deseja atendimento"),
         "reply": "{titular_cpf}", "requires": ["titular_cpf"],
         "notes": "📊 TRÊS redações reais. A terceira — 'Para prosseguirmos vou precisar de alguns "
                  "dados para melhor atendê-lo. Por favor informe o *CPF ou CNPJ* que deseja "
                  "atendimento' (3 sessões) — NÃO casava com a âncora da família HDI, e é a "
                  "primeira tela do atendimento: o corredor emudecia na porta de entrada"},
        {"step": "informar_nome",
         "anchor": r"me informe (?:o )?seu \*?nome\*? ou como|informe o seu nome ou como gostaria de ser chamad",
         "reply": "Atendimento",
         "notes": "📊 'Me informe seu *nome* ou como *gostaria de ser chamado*.' (3 sessões) — a "
                  "família de auto exigia 'informe O SEU nome' e não casava. A resposta é a MESMA "
                  "do corredor de auto: quem opera o canal é a corretora"},
        {"step": "perfil",
         "anchor": (r"escolha a op[çc][ãa]o que melhor te representa|"
                    r"em qual dessas op[çc][õo]es voc[êe] se enquadra"),
         "reply": "Sou corretor(a)",
         "notes": "📊 duas redações, 3 sessões cada, MESMOS botões: 'Sou segurado(a) / Sou "
                  "corretor(a) / Outro'. Agimos em nome da corretora"},
        {"step": "pessoa_no_local",
         "anchor": r"[ée] a pessoa que est[áa] (?:no )?local para acompanhar",
         "reply": "Não",
         "notes": "📊 'Saionara você é a pessoa que está local para acompanhar o serviço?' "
                  "(3 sessões) — quem opera o canal não é quem espera o técnico"},
        {"step": "nome_pessoa_local",
         "anchor": (r"nome da pessoa respons[áa]vel por acompanhar o t[ée]cnico|"
                    r"nome da pessoa que estar[áa] na resid[êe]ncia para receber o t[ée]cnico|"
                    r"qual [ée] o nome da pessoa que est[áa] no local"),
         "reply": "{pessoa_no_local}", "requires": ["pessoa_no_local"],
         "notes": "📊 DUAS redações residenciais (3 sessões cada), nenhuma delas casando com a "
                  "âncora de auto da família. Aqui não há 'only_subservices': em residencial "
                  "SEMPRE tem alguém esperando o técnico"},
        {"step": "telefone_local",
         "anchor": r"n[úu]mero de (?:celular|telefone)\*? com ddd da pessoa que est[áa] no local",
         "reply": "{telefone_contato}", "requires": ["telefone_contato"],
         "notes": "âncora REUSADA da família (casa palavra por palavra: 6 de 6 sessões). 📊 A URA "
                  "recusa telefone mal formatado e repete a MESMA pergunta — a âncora pega as duas"},
        {"step": "telefone_confirma",
         "anchor": r"o n[úu]mero de telefone .{0,24}est[áa] correto", "reply": "Sim",
         "notes": "âncora REUSADA da família (6 ocorrências medidas no residencial da Yelum)"},
        {"step": "endereco_da_apolice",
         "anchor": (r"localizamos o seguinte endere[çc]o|"
                    r"para esse cpf est[áa] cadastrado o endere[çc]o"),
         "reply": "", "noop": True,
         "notes": "📊 'Para esse CPF informado localizamos o seguinte endereço: *Rua:* ... "
                  "*Numero:* ...' — INFORMATIVO, e vem logo antes da confirmação. Responder aqui "
                  "adianta uma resposta para a tela errada. O endereço é o DA APÓLICE: a URA já o "
                  "tem, e é por isso que não existe passo pedindo endereço neste corredor"},
        {"step": "confirma_endereco",
         "anchor": r"voc[êe] confirma (?:o|este) endere[çc]o", "reply": "Sim",
         "notes": "📊 'Você confirma este endereço?' — 6 de 6 sessões. A âncora da família exigia "
                  "'confirma O endereço' e não casava em NENHUMA. Confirmar aqui é seguro: o "
                  "endereço foi lido do cadastro da apólice, não digitado por nós"},
        {"step": "casa_ou_condominio",
         "anchor": (r"resid[êe]ncia [ée] uma casa individual ou est[áa] localizada em um condom[íi]nio|"
                    r"sua resid[êe]ncia [ée] uma casa ou fica em um condom[íi]nio"),
         "reply": "{tipo_imovel}", "fallback_adaptive": True,
         "notes": "📊 NÃO EXISTE NA HDI. Duas redações (3 e 2 sessões) com RÓTULOS DIFERENTES: "
                  "'Casa / Condomínio' e 'Casa / Condomínio/prédio'. Por isso não há resposta fixa "
                  "e o adaptativo guardado escolhe o rótulo que está NA TELA. E não vira slot "
                  "obrigatório: o tipo de imóvel é exigência DESTA seguradora, não do trabalho — "
                  "`_RESID_SLOTS_BASE` só carrega o que todo encanador precisa"},
        {"step": "ponto_referencia",
         "anchor": r"preciso que voc[êe] me informe pelo menos uma refer[êe]ncia",
         "reply": "{ponto_referencia}", "fallback_adaptive": True,
         "notes": "📊 'Agora, preciso que você me informe pelo menos uma referência. *Ex: Próximo "
                  "ao Banco Z...*' — 6 de 6 sessões, a tela mais frequente do corredor. Sem "
                  "referência no caso, o adaptativo responde o que a corretora respondeu de fato "
                  "('sem referencia')"},
        {"step": "servico_ja_aberto",
         "anchor": r"localizamos (?:o servi[çc]o de|algumas assist[êe]ncias).{0,80}?deseja acompanhar",
         "reply": "Novo serviço",
         "notes": "📊 DUAS redações: 'localizamos o serviço de *CHAVEIRO RESIDENCIAL*' e "
                  "'localizamos algumas assistências'. A segunda não casava com a âncora da HDI. "
                  "O corredor abre o que o cliente pediu HOJE; acompanhar chamado antigo é outro "
                  "trabalho, e quem decide é o atendente"},
        {"step": "menu_servico_residencial",
         "anchor": r"qual (?:[ée] )?o servi[çc]o que voc[êe] precisa",
         "reply": "{tipo_servico_opcao}", "requires": ["tipo_servico_opcao"],
         "notes": "📊 lista real: Encanador / Desentupimento / Eletricista / Chaveiro / "
                  "**Linha branca** / Ar condicionado / Voltar — e numa sessão também Linha marrom "
                  "e Dedetização. 'Linha branca' é o nome que a Yelum dá a eletrodoméstico: "
                  "responder 'Eletrodoméstico' (rótulo da HDI) aperta tecla inexistente"},
        {"step": "recado_de_cobertura",
         "anchor": (r"para continuar com a sua solicita[çc][ãa]o temos um recado|"
                    r"reparos emergenciais em virtude de vazamento|"
                    r"m[ãa]o de obra para reparos emergenciais em tomadas"),
         "reply": "", "noop": True,
         "notes": "📊 texto de COBERTURA por subserviço, enviado depois da escolha. Informativo: "
                  "vai ao dossiê e o corredor segue (o conteúdo está em `coverage_guardrails`)"},
        {"step": "detalhe_do_vazamento",
         "anchor": r"(?:qual desses itens est[áa] com vazamento|e onde [ée] o vazamento)",
         "reply": "{vazamento_local}", "requires": ["vazamento_local"],
         "fallback_adaptive": True, "only_subservices": ["encanador"],
         "notes": "📊 'Qual desses itens está com vazamento? Torneira / Torneira elétrica / Sifão / "
                  "Chuveiro / Válvulas de descarga / Registro / Mais opções / Voltar' — e a "
                  "variante 'Certo! E onde é o vazamento?' com a MESMA lista. Encaixa no slot "
                  "`vazamento_local`, que já existia porque é pergunta do TRABALHO"},
        {# 🔴 O CHUVEIRO É TRABALHO DO ELETRICISTA, E ESTE PASSO É DO ENCANADOR.
    #
    # 📊 O conferidor achou (regra C, 2 sessões): a tela "Selecione em qual
    #    ambiente está o CHUVEIRO — Suíte / Banheiro social / Área" só aparece em
    #    sessões de ELETRICISTA, e era respondida por um passo restrito a
    #    `encanador`.
    #
    # ⚠️ E a cobertura confirma: o texto do eletricista da família yelum/hdi diz
    #    "troca de chuveiros ou resistências de chuveiros ou torneiras elétricas".
    #    Chuveiro elétrico é elétrica; cano de chuveiro é hidráulica. A URA
    #    pergunta o CÔMODO nos dois casos, com a mesma frase.
    "step": "comodo_do_vazamento",
         "anchor": r"em qual c[ôo]modo|selecione em qual ambiente est[áa] o chuveiro",
         "reply": "", "fallback_adaptive": True, "only_subservices": ["encanador", "eletricista"],
         "notes": "📊 'Em qual cômodo? Cozinha / Banheiro / Lavanderia' e 'Selecione em qual "
                  "ambiente está o chuveiro: Suíte / Banheiro social / Área externa'. Rótulos "
                  "DIFERENTES por caminho — sem resposta fixa, quem escolhe é o adaptativo, "
                  "lendo a tela e a descrição do problema"},
        {"step": "detalhe_eletrico",
         "anchor": (r"op[çc][ãa]o que corresponde com o seu problema|"
                    r"selecione abaixo qual [ée] o problema el[ée]trico"),
         "reply": "", "fallback_adaptive": True, "only_subservices": ["eletricista"],
         "notes": "📊 'Falta de energia / Problema elétrico' e depois 'Tomadas / Interruptores / "
                  "Lâmpadas / Reatores queimados / Disjuntores/fusíveis / Chuveiro / Torneira "
                  "elétrica'. 2 sessões cada"},
        {"step": "periodo_preferido",
         "anchor": r"qual o melhor per[íi]odo",
         "reply": "{periodo_preferido}", "fallback_adaptive": True,
         "notes": "📊 'Qual o melhor período? Manhã (08h às 12h) / Tarde (13h às 18h)' — 1 sessão. "
                  "Só aparece depois de escolher AGENDAR. `periodo_preferido` já é slot do "
                  "residencial (vai no resumo ao humano)"},
        {"step": "aguarde",
         "anchor": (r"ainda n[ãa]o identificamos a sua resposta|sua resposta est[áa] diferente do que solicitamos|"
                    r"assist[êe]ncia solicitada|sua assist[êe]ncia j[áa] est[áa] em andamento|"
                    r"o qu[ãa]o satisfeito voc[êe] est[áa]|gostaria de saber o que voc[êe] achou|"
                    r"muito obrigada por ter respondido|foi um prazer te atender|"
                    r"se precisar esclarecer mais alguma d[úu]vida"),
         "reply": "", "noop": True,
         "notes": "📊 avisos, confirmações e PESQUISA DE SATISFAÇÃO. A pesquisa vem depois do "
                  "protocolo e não é parte do acionamento: responder nota de atendimento em nome "
                  "do segurado é opinião que não é nossa"},
        {"step": "deseja_continuar",
         "anchor": r"deseja continuar (?:este|com o) atendimento", "reply": "Sim",
         "notes": "âncora REUSADA da família (3 sessões medidas no residencial)"},
    ],
    "subservices": {
        "encanador": {"tipo_servico_opcao": "Encanador", "required_slots": _resid_slots("encanador")},
        "desentupimento": {"tipo_servico_opcao": "Desentupimento", "required_slots": _resid_slots("desentupimento")},
        "eletricista": {"tipo_servico_opcao": "Eletricista", "required_slots": _resid_slots("eletricista")},
        "chaveiro": {"tipo_servico_opcao": "Chaveiro", "required_slots": _resid_slots("chaveiro")},
        # 🔴 "Linha branca", não "Eletrodoméstico". A chave é a CANÔNICA do
        # produto; o rótulo é o que está escrito na tela da Yelum.
        "eletrodomesticos": {"tipo_servico_opcao": "Linha branca", "required_slots": _resid_slots("eletrodomesticos")},
    },
    "subservice_labels": {
        "encanador": "encanador", "desentupimento": "desentupimento",
        "eletricista": "eletricista", "chaveiro": "chaveiro",
        "eletrodomesticos": "reparo de eletrodomestico (linha branca)",
    },
    "opening_template": _RESID_OPENING_TEMPLATE,
    "human_phase_guidance": _RESID_HUMAN_PHASE_GUIDANCE,
    "capture_anchors": dict(_AUTO_CAPTURE_ANCHORS),
    # 🔴 AQUI a Yelum tem o que a HDI não tinha. O corredor da HDI declara
    # `client_instructions: []` com a nota de que a regra do maior de 18 anos e a
    # da senha "são da Allianz — copiá-las para cá seria inventar". Na YELUM elas
    # são MEDIDAS, palavra por palavra, em 3 sessões cada.
    "client_instructions": [
        "📊 A senha da visita técnica são os 4 ÚLTIMOS DÍGITOS do celular informado da pessoa que "
        "estará no local (ou do WhatsApp que pediu a assistência). Ela deve ser repassada ao "
        "técnico assim que ele chegar — sem a senha, o prestador não executa o serviço.",
        "📊 É necessária a presença de uma pessoa MAIOR DE 18 ANOS no local para receber e "
        "acompanhar o prestador. Se for preciso trocar peças, o material fica por conta do "
        "segurado (a mão de obra é que está coberta).",
    ],
    "handoff_triggers": _RESID_HANDOFF_TRIGGERS + [
        # 📊 '*Saionara - Resulta*, por ser um item essencial, vou te transferir
        # para que um de nossos analistas de continuidade ao atendimento.' A
        # própria URA declara que dali em diante quem atende é gente.
        r"vou te transferir para",
        # 🔴 O gatilho de formulário nativo FICA. Ele saiu dos corredores de AUTO
        # da HDI/Yelum em 03/08/2026 porque o canal de resposta foi provado E o
        # schema estava capturado. Aqui não há schema: `native_flows` não é
        # declarado, e nenhum formulário RESIDENCIAL foi observado. Sem schema
        # não há o que responder, e a única saída honesta é pausar com o dossiê.
        r"formulario nativo",
    ],
    "finalize_anchors": [
        # 📊 'Você precisa do atendimento agora ou prefere agendar para outro
        # momento? Botão 1: Agora' — 4 de 6 sessões. É a redação SEM o "para",
        # a que a âncora literal antiga não pegava. Responder ABRE o serviço.
        _HDI_FAMILY_AGORA_OU_AGENDAR,
        r"podemos confirmar", r"posso confirmar", r"deseja confirmar",
    ],
    "finalize_abort_reply": "Sair",
    "unknown_step_policy": "pause_and_handoff",
    "coverage_guardrails": [
        "📊 ENCANADOR: 'Reparos emergenciais em virtude de vazamento (aparente) em tubulações em PVC "
        "de 1 a 4 polegadas, ou em dispositivos hidráulicos como: torneiras, sifões, encanamento de "
        "chuveiros, válvulas de descarga, boia de caixa d'água.' Vazamento NÃO aparente e tubulação "
        "fora dessa bitola não estão nesta cobertura.",
        "📊 ELETRICISTA: 'Mão de obra para reparos emergenciais em tomadas queimadas, interruptores "
        "defeituosos, troca de lâmpadas ou reatores queimados, disjuntores e fusíveis danificados, "
        "troca de chuveiros ou resistências (não blindados).' Chuveiro BLINDADO está fora.",
        "📊 LINHA BRANCA: 'Está coberto a mão de obra e peças (até o limite de cobertura contratada) "
        "para reparo de eletrodomésticos com defeito no mecanismo — para equipamentos com até 10 "
        "(dez) anos de fabricação.' Aparelho com mais de 10 anos não é acionamento.",
        "📊 A MÃO DE OBRA é o que está coberto: material de troca de peças fica por conta do "
        "segurado, e a própria URA avisa isso antes de abrir.",
        "⚠️ LIMITE DE UTILIZAÇÕES: a HDI (mesmo bot) informa quantas utilizações restam e recusa "
        "quando esgotam. Na YELUM isso NÃO foi observado — 📊 zero ocorrências de 'utilizações' em "
        "3.026 eventos. Por isso este corredor não declara passo nem gatilho de limite: se a tela "
        "aparecer, `unknown_step_policy: pause_and_handoff` devolve o caso ao humano em vez de "
        "improvisar. Destrava quando uma sessão da Yelum trouxer o texto.",
    ],
}


# ==========================================================================
# 🔴 META PASSO: A ÂNCORA QUE SÓ FREIA E NUNCA RESPONDE — 22/08/2026
# ==========================================================================
#
# `_HDI_FAMILY_AGORA_OU_AGENDAR` está declarada nos `finalize_anchors` dos DOIS
# corredores residenciais da família — e em NENHUM deles existe um `ura_step`
# para ela. O corredor de AUTO da mesma família tem o passo desde sempre
# (`quando_agora`, na lista `_YELUM_FAMILY_STEPS`).
#
# 📊 A tela: "Você precisa do atendimento agora ou prefere agendar para outro
#    momento? Botão 1: Agora  Botão 2: Agendar  Botão 3: Voltar"
#    yelum-residencial 4 sessões · hdi-residencial 1 sessão.
#
# 🔴 O EFEITO É DIFERENTE EM CADA MODO, E ISSO ESCONDIA O DEFEITO:
#      · em TESTE, o freio dispara e a sessão encerra limpa — parece correto.
#      · em LIVE, o corredor **emudece exatamente na tela que ABRE o serviço**.
#    Uma âncora que só freia e nunca responde é meio passo. E o meio que falta
#    é justamente o ponto de não-retorno do acionamento.
#
# ⚠️ O passo NÃO tira o freio: os dois convivem, como já convivem no auto.
for _pb_resid in (HDI_RESIDENCIAL_WHATSAPP_V1, YELUM_RESIDENCIAL_WHATSAPP_V1):
    _pb_resid["ura_steps"] = [
        {"step": "quando_agora", "anchor": _HDI_FAMILY_AGORA_OU_AGENDAR,
         "reply": "Agora",
         "notes": "📊 yelum-resid 4 sessões · hdi-resid 1. O MESMO objeto de âncora que "
                  "o freio usa — uma definição, dois leitores. Responder ABRE o serviço."},
    ] + list(_pb_resid["ura_steps"])



# ==========================================================================
# PORTO — TRONCO e GALHO (SPEC-084 BLOCO 1, 22/08/2026)
# ==========================================================================
#
# 📊 A coleta cobriu 220 das 239 telas orfas (92%) e retorno 779 de 806 (96%).
#    As 19 restantes: 16 sao a fase HUMANA de uma sessao so (viram FRONTEIRA,
#    nao passo), 2 sao URLs ja capturadas por `tracking_link`, 1 ja e
#    `handoff_trigger` declarado.
#
# ⚠️ VIES DO MEDIDOR, dito em voz alta: a arvore so consulta `match_ura_step`,
#    nunca `detect_handoff_trigger`. Toda tela que JA e handoff conta como orfa
#    na fila de trabalho. Nao e divida do corredor.
_PORTO_TRONCO = [
    # ---- os que precisam vir ANTES de qualquer noop largo ----------------
    # 🔴 A LARGA ROUBA A ESTREITA: medido, `ajudar_mais_sim_nao` sozinha casa
    #    as 3 telas de tres botoes. A ordem aqui e obrigatoria.
    {"step": "ajudar_mais_3botoes",
     "anchor": r"posso te ajudar com algo mais\?[\s\S]{0,80}novo atendimento",
     "reply": "Encerrar",
     "notes": "📊 3 msgs / 3 sessões. ⚠️ 'Falar com atendente' é a tecla que joga o caso "
              "no humano da seguradora — o oposto do que a SPEC quer."},
    {"step": "ajudar_mais_sim_nao", "anchor": r"posso te ajudar com algo mais\?",
     "reply": "Não", "notes": "📊 9 msgs / 9 sessões."},

    # ---- identificacao ---------------------------------------------------
    # 🔴 A RESPOSTA É "NÃO", E A RAZÃO É A MESMA DO `cpf_anterior`: o WhatsApp é
    #    da CORRETORA e atende N clientes. O nome exibido é o do ÚLTIMO
    #    atendimento. 📊 E as duas saídas foram medidas:
    #       'Sim' -> "digite os 3 ÚLTIMOS DÍGITOS do seu CPF"  (sessão 0fe42179)
    #       'Não' -> "digite o seu *CPF ou CNPJ*"              (sessão 3854b4a2)
    #    Só a segunda re-identifica de verdade.
    {"step": "confirma_titular", "anchor": r"eu estou falando com", "reply": "Não",
     "notes": "📊 auto 8/8 · residencial 4/4. 'Sim' aciona na apólice do cliente anterior."},
    {"step": "tres_ultimos_digitos", "anchor": r"digite os 3 [úu]ltimos d[íi]gitos do seu cpf",
     "reply": "{titular_cpf_3_ultimos}", "requires": ["titular_cpf_3_ultimos"],
     "fallback_adaptive": True, "notes": "📊 auto 1/1 · residencial 1/1."},
    # ⚠️ ANTES de `nao_entendi`: a 2ª redação começa com "Desculpe, não entendi".
    {"step": "cpf_invalido",
     "anchor": r"^desculpe, n[ãa]o entendi a sua resposta[\s\S]{0,60}cpf ou cnpj v[áa]lido",
     "reply": "{titular_cpf}", "requires": ["titular_cpf"],
     "notes": "📊 1/1 auto · 1/1 resid. 🔴 UMA repetição, não duas: a 2ª falha leva a "
              "'Por este canal não podemos seguir', que é handoff."},

    # ---- contato ---------------------------------------------------------
    # 🔴 A PROVA DA ARMADILHA DO `_norm`, MEDIDA NESTA ÂNCORA:
    #    📊 cru = 1 tela · normalizado = 9. Oito das nove só casam DEPOIS do
    #    `_norm`, porque o `*` do negrito está exatamente entre "um " e "número".
    {"step": "informar_celular", "anchor": r"informe um\s*[\s\S]{0,3}n[úu]mero de celular",
     "reply": "{telefone_contato}", "requires": ["telefone_contato"],
     "notes": "📊 auto 9/9 · residencial 3/3."},
    {"step": "telefone_invalido", "anchor": r"esse telefone n[ãa]o [ée] v[áa]lido",
     "reply": "{telefone_contato}", "requires": ["telefone_contato"], "notes": "📊 1/1."},
    {"step": "dois_telefones", "anchor": r"identifiquei dois telefones para contato",
     "reply": "", "noop": True, "notes": "📊 auto 2/2 · resid 1/1."},
    {"step": "nome_no_local",
     "anchor": r"qual [ée] o nome de quem estar[áa] (?:no local|na resid[êe]ncia)",
     "reply": "{pessoa_no_local}", "requires": ["pessoa_no_local"],
     "notes": "📊 auto 6/6 · residencial 3/3."},

    # ---- veiculo ---------------------------------------------------------
    {"step": "cor_do_veiculo", "anchor": r"(?:selecione|informe) a cor do ve[íi]culo",
     "reply": "{veiculo_cor}", "fallback_adaptive": True,
     "notes": "📊 11 msgs / 11 sessões, DUAS listas. 🔴 A ESCAPATÓRIA É DIFERENTE: na "
              "lista A a tecla honesta sem cor é 'Não sei a cor'; na B ela NÃO EXISTE — "
              "'Outra cor' abre texto livre (`cor_do_veiculo_livre`)."},
    {"step": "cor_do_veiculo_livre", "anchor": r"ent[ãa]o escreva qual a cor",
     "reply": "{veiculo_cor}", "fallback_adaptive": True, "notes": "📊 3 msgs / 3 sessões."},
    {"step": "mais_de_um_veiculo", "anchor": r"identifiquei mais de um ve[íi]culo nesse (?:cpf|cnpj)",
     "reply": "", "noop": True, "notes": "📊 3/3. É CARDÁPIO: a escolha é a tela seguinte."},
    # 🔴 IDENTIFICADA, NÃO RESOLVIDA — ver PENDENCIAS. 📊 As 3 telas trazem entradas
    #    DUPLICADAS (mesmo modelo, ano e placa MASCARADA em posições diferentes).
    #    Posição fixa é impossível; casar por placa é ambíguo com máscara.
    {"step": "escolher_veiculo", "anchor": r"^qual o ve[íi]culo\?",
     "reply": "{veiculo_opcao}", "fallback_adaptive": True,
     "notes": "📊 3 telas / 3 sessões. 🔴 Sem match seguro pela placa, o adaptativo "
              "decide e, falhando, é handoff — nunca posição fixa."},

    # ---- endereco --------------------------------------------------------
    {"step": "aviso_onde_o_veiculo_estara",
     "anchor": (r"voc[êe] vai precisar informar\s*[\s\S]{0,10}onde o ve[íi]culo|"
                r"preciso saber\s*[\s\S]{0,10}onde o ve[íi]culo est"),
     "reply": "", "noop": True,
     "notes": "📊 12 msgs / 12 sessões, TRÊS redações. É ANÚNCIO: a pergunta vem depois "
              "('Digite o endereço completo'), e quem responde é `endereco_livre`. "
              "O `[\\s\\S]{0,10}` existe porque o `*` do negrito some no `_norm` e "
              "sobra o espaço."},
    {"step": "selecionar_botao_formulario", "anchor": r"^\s*selecione o bot[ãa]o\s*:\s*$",
     "reply": "", "noop": True,
     "notes": "📊 12 msgs / 12 sessões. É o rótulo do botão do FORMULÁRIO nativo. "
              "🔴 O `^...$` sem MULTILINE é o que impede roubar 'Não entendi sua "
              "resposta. Selecione o botão abaixo para escolher uma das opções.'"},
    {"step": "endereco_nao_localizado", "anchor": r"n[ãa]o consegui localizar o endere[çc]o",
     "reply": "", "noop": True, "notes": "📊 2/2."},
    {"step": "localizacao_atual",
     "anchor": r"caso voc[êe] esteja no mesmo local, compartilhe a sua localiza[çc][ãa]o",
     "reply": "", "noop": True,
     "notes": "📊 2/2. A URA pede o PIN nativo do WhatsApp; o corredor não manda pin."},
    {"step": "complemento", "anchor": r"digite (?:ent[ãa]o )?um\s*[\s\S]{0,3}complemento",
     "reply": "{local_complemento}", "fallback_adaptive": True,
     "notes": "📊 auto 6/6 · resid 3/3. A própria URA dá o default: 'não tem'."},

    # ---- avisos e regras que vao ao CLIENTE, nunca respondidos ------------
    {"step": "aviso_maior_de_18", "anchor": r"necess[áa]rio ter algu[ée]m maior de 18 anos",
     "reply": "", "noop": True,
     "notes": "📊 auto 11/11 · residencial 4/4 — a tela mais universal do corredor. "
              "O texto vive em `client_instructions`."},
    {"step": "garantia_90_dias", "anchor": r"garantia de\s*[\s\S]{0,3}90 dias",
     "reply": "", "noop": True, "notes": "📊 5 msgs / 4 sessões."},
    {"step": "recado_peca_20_dias", "anchor": r"voc[êe] tem at[ée]\s*[\s\S]{0,3}20 dias corridos",
     "reply": "", "noop": True, "notes": "📊 4/4."},
    {"step": "saldo_de_servicos",
     "anchor": r"voc[êe] tem dispon[íi]vel\s*[\s\S]{0,6}servi[çc]os? de assist[êe]ncia para sua casa",
     "reply": "", "noop": True,
     "notes": "📊 3/3. 🔴 CONTROLE (c): cru = 0, normalizado = 3 — só casa depois do "
              "`_norm`, porque a URA escreve '*02* *serviços*'."},
    {"step": "servico_sai_do_seguro_auto", "anchor": r"ser[áa] solicitado no seguro do ve[íi]culo",
     "reply": "", "noop": True,
     "notes": "📊 3/3. Não é erro: é como a Porto amarra a assistência residencial ao "
              "seguro do veículo. Vai ao cliente para ele não estranhar."},

    # ---- desfecho --------------------------------------------------------
    {"step": "resumo_confira", "anchor": r"confira o resumo da sua solicita[çc][ãa]o",
     "reply": "", "noop": True, "notes": "📊 5 msgs / 4 sessões. CARDÁPIO: a escolha vem depois."},
    {"step": "protocolo_recebido", "anchor": r"aqui est[áa] (?:o )?seu protocolo de atendimento",
     "reply": "", "noop": True,
     "notes": "📊 auto 11/11 · residencial 5/4. É o DESFECHO. Quem lê o número é "
              "`capture_anchors.protocol`; o passo existe para o motor ficar calado "
              "enquanto a captura acontece."},
    {"step": "desfecho_agendado", "anchor": r"tudo certo com o seu (?:agendamento|reagendamento)",
     "reply": "", "noop": True,
     "notes": "📊 auto 11/11 · residencial 5/4. 🔴 TRÊS redações e só UMA é capturada "
              "hoje ('em até 60 minutos' -> eta). As duas com 'no dia X, entre Yh e Zh' "
              "não são — ver `schedule_porto` em PENDENCIAS."},
    {"step": "link_acompanhamento",
     "anchor": r"acompanhar o andamento desse servi[çc]o\s*[\s\S]{0,3} no link abaixo",
     "reply": "", "noop": True, "notes": "📊 resid 4/4 · auto 2/2."},
    {"step": "avaliacao_nps",
     "anchor": (r"a sua opini[ãa]o [ée] muito importante|"
                r"clique em \"?avaliar atendimento\"?|agrade[çc]o sua avalia[çc][ãa]o"),
     "reply": "", "noop": True,
     "notes": "📊 14 msgs / 11 sessões. Pós-desfecho. 🔴 Responder pesquisa de satisfação "
              "em nome do segurado é escrever opinião que não é nossa. "
              "⚠️ Vem ANTES de `nao_entendi`, que também casaria 'Não entendi o que você "
              "digitou. Por favor, clique em *Avaliar atendimento*'."},

    # ---- fim de conversa e erro (o noop largo, POR ULTIMO) ----------------
    {"step": "continuar_atendimento", "anchor": r"voc[êe] ainda quer continuar o seu atendimento",
     "reply": "Sim",
     "notes": "📊 auto 5/5 · resid 4/4. É sonda de inatividade. 'Sim' mantém viva a "
              "sessão que importa e só prolonga a que já acabou; 'Não' mata as duas."},
    {"step": "alterar_informacao_botao", "anchor": r"gostaria de alterar alguma informa[çc][ãa]o",
     "reply": "Não, está tudo correto", "notes": "📊 resid 4/4 · auto 2/2."},
    {"step": "saudacao_de_volta", "anchor": r"bom ter voc[êe] de volta", "reply": "", "noop": True,
     "notes": "📊 auto 5 · resid 5. 🔴 A âncora do `aguarde` exige 'QUE bom ter você de "
              "volta'; 8 telas escrevem 'Olá! {NOME} BOM ter você de volta', sem o 'que'. "
              "Tirar a palavra recupera as 8 e não perde as que já casavam."},
    {"step": "mudar_de_opcao_voltar",
     "anchor": r"se quiser mudar de op[çc][ãa]o, digite\s*[\s\S]{0,3}voltar",
     "reply": "", "noop": True,
     "notes": "📊 auto 5/5 · resid 7/7. DUAS grafias: 'digite *voltar*' e 'digite voltar'."},
    {"step": "encerrar_conversa",
     "anchor": (r"vou encerrar a conversa|quando precisar,? [ée] s[óo] chamar|"
                r"quando quiser falar sobre a porto|agrade[çc]o o seu contato|"
                r"se quiser encerrar o atendimento, [ée] s[óo] digitar sair|"
                r"como voc[êe] n[ãa]o respondeu eu vou encerrar"),
     "reply": "", "noop": True, "notes": "📊 auto 17/13 · resid 6/6."},
    # 🔴 POR ÚLTIMO, e é decisão que ficou em aberto: ver PENDENCIAS.
    #    Na porto "Não entendi a sua resposta" é a URA ESPERANDO — silêncio vira
    #    timeout. O certo parece ser REENVIAR a última resposta, e isso é
    #    comportamento de MOTOR, não de âncora. Não existe hoje, e não se inventa.
    {"step": "nao_entendi",
     "anchor": (r"n[ãa]o entendi (?:o que voc[êe] digitou|a sua resposta|sua resposta)|"
                r"ainda n[ãa]o consegui entender|op[çc][ãa]o inv[áa]lida|"
                r"n[ãa]o consegui te entender"),
     "reply": "", "noop": True,
     "notes": "📊 auto 10/6 · resid 2/2. 🔴 noop é o menos pior, não o certo — a URA "
              "está esperando. Registrado em PENDENCIAS como decisão de motor."},
    {"step": "cliente_personalizado", "anchor": r"grupo de clientes com atendimento personalizado",
     "reply": "", "noop": True, "notes": "📊 2/2."},
    {"step": "aviso_automatico", "anchor": r"a mensagem que voc[êe] recebeu [ée] um aviso autom[áa]tico",
     "reply": "", "noop": True, "notes": "📊 2/2."},
]

# 🔴 NOTIFICAÇÃO ATIVA DE SINISTRO — 11 das 143 órfãs, e NENHUMA é trabalho de
#    corredor. 📊 12 msgs / 4 sessões: a porto NOTIFICA a corretora sobre etapa de
#    sinistro (Check-in, Reparos iniciados, Veículo entregue, vistoria agendada).
#    Chegam sem que ninguém tenha aberto conversa.
_PORTO_AVISO_SINISTRO = {
    "step": "aviso_sinistro_proativo",
    "anchor": (r"assistente virtual da porto[\s\S]{0,200}"
               r"(?:sinistro de n[úu]mero|para o sinistro|vistoria do seu ve[íi]culo)"),
    "reply": "", "noop": True,
    "notes": "📊 12 msgs / 4 sessões, 11 telas distintas. NÃO é URA de acionamento.",
}

PORTO_AUTO_WHATSAPP_V1["ura_steps"] = (
    list(PORTO_AUTO_WHATSAPP_V1["ura_steps"])
    + [dict(p) for p in _PORTO_TRONCO] + [dict(_PORTO_AVISO_SINISTRO)]
)
PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = (
    list(PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"]) + [dict(p) for p in _PORTO_TRONCO]
)

# 🔴 A PORTO OFERECE UM SEGUNDO WHATSAPP QUANDO A APÓLICE É ITAÚ.
#    📊 8 msgs / 2 sessões. E o produto tem `_OPERADO_POR = {'itau': 'porto'}`,
#    que resolve a direção CONTRÁRIA. Aqui a porto RECUSA a apólice.
#    ⚠️ Como é `handoff_trigger`, NÃO TEM DOTALL: o `[\s\S]` é obrigatório.
PORTO_AUTO_WHATSAPP_V1["handoff_triggers"] = PORTO_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    r"n[ãa]o localizei as suas informa[çc][õo]es na porto",
    r"o atendimento [ée] no\s*[\s\S]{0,3}whatsapp da ita[úu]",
    r"porto\.vc/(?:wpp-)?itau",
    # 📊 `_AUTO_HANDOFF_TRIGGERS` tem `sinistro|colisão|acidente` mas NÃO tem
    #    `furto` nem `roubo`, e a porto oferece "Relatar furto ou roubo" no menu.
    r"relatar furto ou roubo",
]


# ==========================================================================
# YELUM + HDI — A FAMILIA RESIDENCIAL (SPEC-084 BLOCO 1, 22/08/2026)
# ==========================================================================
#
# 🔴 O PIOR CASO DO PRODUTO, e ele estava escondido numa combinação:
#
#      📊 hdi-residencial: 70 telas distintas · 64 SEM PASSO · 6 ura_steps
#      📊 unknown_step_policy = "pause_and_handoff"
#
#    Nos corredores de AUTO a política é `adaptive_then_handoff`: tela órfã cai
#    no cérebro e o fluxo continua. Aqui é `pause_and_handoff`: **cada uma das
#    64 telas órfãs PARA o acionamento e chama um humano.** Um corredor com 6
#    passos e 64 paradas não é um corredor incompleto — é um corredor que
#    GARANTE handoff.
#
# 🔴 E a medição que reordena o trabalho: **35 dessas 64 já são respondidas,
#    palavra por palavra, pelo corredor `YELUM_RESIDENCIAL_WHATSAPP_V1`.**
#    Rodado com o motor real, o controle inverso deu ZERO nas outras três
#    direções (yelum-resid <- hdi-resid = 0; e auto <-> auto = 0 porque auto
#    JÁ compartilha `_YELUM_FAMILY_STEPS` por referência).
#
#    A hdi-residencial não precisa de 64 passos novos. Precisa de UMA LISTA.
#
# ⚠️ E o que NÃO pode ser compartilhado — a medição diz por quê:
#
#      `utilizacoes_restantes` e o gatilho "não possui mais utilizações"
#          📊 "utilizações": HDI 4 ocorrências, **Yelum ZERO em 3.026 eventos**
#      `menu_servico_residencial` (o rótulo)
#          📊 a Yelum escreve "Linha branca"; a HDI escreve "Eletrodoméstico".
#          🔴 RÓTULO DE MENU NUNCA É FAMÍLIA.
#      `desambiguacao_veiculo_ou_residencial` (a resposta)
#          a tela é igual; o corredor de AUTO responde "Automóvel" na MESMA tela.
#
#    Os três já existem no corredor da HDI, e a lista da família entra DEPOIS —
#    `match_ura_step` devolve o primeiro que casa, então o específico vence.
HDI_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = (
    list(HDI_RESIDENCIAL_WHATSAPP_V1["ura_steps"])
    + [dict(p) for p in YELUM_RESIDENCIAL_WHATSAPP_V1["ura_steps"]]
)

# ==========================================================================
# YELUM + HDI — TRONCO e GALHO
# ==========================================================================
_FAMILIA_YH_TRONCO = [
    # ---- o ECO do endereco: e a tela ANTES da confirmacao ----------------
    # 🔴 A prova de que é noop veio da SEQUÊNCIA, não do texto: em 3 sessões
    #    medidas (8ce9f29d, 86769bd5, 71caf82f) a tela vem IMEDIATAMENTE antes
    #    de "Você confirma o endereço?", que já tem passo. Responder aqui
    #    adianta a resposta para a tela errada.
    {"step": "endereco_geocodificado",
     "anchor": (r"esse foi o endere[çc]o mais pr[óo]ximo que encontramos|"
                r"o endere[çc]o pode variar alguns metros"),
     "reply": "", "noop": True, "notes": "📊 6 telas / 25 ocorrências-sessão."},

    # ---- o endereco partido em TRES telas (a URA de 2026) ----------------
    # 🔴 O passo `complemento_ref` existente (`quais são o complemento e/ou
    #    referência`) é da URA ANTIGA. A de 2026 partiu a pergunta em DUAS
    #    telas — um slot só respondendo as duas manda o complemento na tela
    #    da referência.
    {"step": "falta_pouco", "anchor": r"falta pouco para finalizarmos essa etapa",
     "reply": "", "noop": True, "notes": "📊 yelum 9 ses · hdi 5 ses."},
    {"step": "complemento_endereco", "anchor": r"digite um \*?complemento\*?",
     "reply": "{local_complemento}", "fallback_adaptive": True,
     "notes": "📊 yelum 9 ses · hdi 5 ses. A própria URA dá o default: 'não tem'."},
    {"step": "ponto_referencia_auto", "anchor": r"digite um ponto de \*?refer[êe]ncia",
     "reply": "{ponto_referencia}", "fallback_adaptive": True,
     "notes": "📊 yelum 9 ses · hdi 5 ses."},

    # ---- o DESFECHO: 47 telas distintas colapsam em TRES passos ----------
    # 🔴 A árvore conta TEXTO DISTINTO, e cada protocolo cria um texto novo —
    #    então 47 telas de desfecho aparecem como 47 FOLHAS de retorno 1.
    #    São TRÊS passos.
    {"step": "resumo_da_solicitacao", "anchor": r"\*?resumo da solicita[çc][ãa]o\*?",
     "reply": "", "noop": True,
     "notes": "📊 22 telas. ⚠️ É aqui que `_ANCORA_DE_PROTOCOLO` dispara "
              "('*Assistência:* 9666474'); o passo ser noop é o que garante que o "
              "corredor fique calado enquanto a captura acontece."},
    {"step": "finalizamos_a_abertura", "anchor": r"finalizamos a abertura do\(s\) pedido\(s\)",
     "reply": "", "noop": True, "notes": "📊 18 telas."},
    {"step": "notificacao_do_prestador",
     "anchor": (r"estamos buscando o prestador|encontramos o prestador que realizar[áa]|"
                r"n[ãa]o encontramos o prestador para a assist|"
                r"est[áa] a caminho e faltam aproximadamente|"
                r"a previs[ãa]o de chegada informada para o servi[çc]o|"
                r"chegar[áa] para te atender entre"),
     "reply": "", "noop": True, "notes": "📊 7 telas (hdi-auto)."},

    # ---- pesquisa de satisfacao: opiniao que nao e nossa ------------------
    # 🔴 O corredor RESIDENCIAL da Yelum já tem esta regra escrita; o de AUTO
    #    não tinha. Um mesmo bot, duas decisões: é esquecimento, não escopo.
    {"step": "pesquisa_satisfacao",
     "anchor": (r"gostaria de saber o que voc[êe] achou dest|"
                r"o qu[ãa]o satisfeito voc[êe] est[áa]|"
                r"muito obrigada por ter respondido"),
     "reply": "", "noop": True, "notes": "📊 yelum 3 telas / 22 ses · hdi 3 / 14."},

    # ---- fim de conversa: tres telas, tres significados -------------------
    # 🔴 `encerrada_por_inatividade` NÃO é um noop qualquer: a URA DESLIGOU. Um
    #    corredor que trata isso como "mensagem informativa" fica monitorando uma
    #    conversa que não existe mais — a família dos `corridor_runs` abandonados.
    #    ⚠️ O sinal terminal que ele precisa (`terminal: True` ou entrada em
    #    handoff) é MUDANÇA DE CONTRATO de `ura_steps`, e está em PENDENCIAS.
    {"step": "encerrada_por_inatividade",
     "anchor": (r"por falta de intera[çc][ãa]o esta conversa foi encerrada|"
                r"tempo maximo de espera para este atendimento foi excedido|"
                r"esta conversa ser[áa] encerrada"),
     "reply": "", "noop": True,
     "notes": "📊 yelum 2 telas / 7 ses · hdi 1 / 2. 🔴 A URA DESLIGOU — noop é o "
              "menos pior, não o certo. Ver PENDENCIAS."},
    {"step": "seguimos_a_disposicao", "anchor": r"seguimos [àa] disposi[çc][ãa]o",
     "reply": "", "noop": True, "notes": "📊 yelum 6 ses · hdi 5 ses."},
    # 🔴 "Sua resposta está diferente do que solicitamos" significa que a NOSSA
    #    última resposta foi RECUSADA. Noop puro faz o corredor esperar em
    #    silêncio até o timeout. A trava (contador -> needs_human) é de MOTOR.
    {"step": "resposta_recusada",
     "anchor": (r"sua resposta est[áa] diferente do que solicitamos|"
                r"precisamos que siga [àa]s orienta[çc][õo]es anteriores"),
     "reply": "", "noop": True,
     "notes": "📊 yelum 6 ses · hdi 1 ses. 🔴 É recusa da NOSSA resposta, não aviso. "
              "Ver PENDENCIAS."},

    # ---- avisos com regra de DINHEIRO -------------------------------------
    {"step": "aviso_recarga_bateria",
     "anchor": r"enviaremos um prestador para realizar a \*?recarga da sua bateria",
     "reply": "", "noop": True,
     "notes": "📊 7 ocorrências-sessão. 🔴 Contém regra de DINHEIRO: 'caso seja "
              "necessário a compra de uma nova bateria, o segurado será responsável "
              "pela negociação diretamente com o prestador'. Vai a `regras_para_o_cliente`."},

    # ---- pos-protocolo ----------------------------------------------------
    {"step": "assistencia_solicitada",
     "anchor": r"assist[êe]ncia solicitada. sua solicita[çc][ãa]o est[áa] em andamento",
     "reply": "", "noop": True, "notes": "📊 yelum 5 ses · hdi 2 ses."},
    {"step": "deu_tudo_certo",
     "anchor": r"deu tudo certo com a sua solicita[çc][ãa]o ou ainda precisa de ajuda",
     "reply": "Tudo certo", "fallback_adaptive": True,
     "notes": "📊 yelum 5 ses · hdi 2 ses. 🔴 A resposta certa depende de um FATO do "
              "run (o protocolo foi capturado?), e o passo não vê o run. Com "
              "`fallback_adaptive`, sem protocolo o cérebro decide. Ver PENDENCIAS."},

    # ---- agendamento -------------------------------------------------------
    {"step": "agendamento_data", "anchor": r"para qual data deseja fazer o agendamento",
     "reply": "{data_agendamento}", "fallback_adaptive": True, "notes": "📊 yelum 2 · hdi 1."},
    # 🔴 O `^` é OBRIGATÓRIO: sem ele a alternativa roubaria as telas de horário
    #    de condomínio do residencial. `match_ura_step` usa IGNORECASE|DOTALL
    #    SEM MULTILINE, então `^` é o início da mensagem inteira.
    {"step": "agendamento_hora", "anchor": r"^em qual hor[áa]rio",
     "reply": "{hora_agendamento}", "fallback_adaptive": True, "notes": "📊 yelum 2 · hdi 1."},

    # ---- CONDOMINIO: sem os dois horarios, o prestador nao entra no predio --
    # 🔴 A URA ERRA A PRÓPRIA GRAFIA: "condoNÍmio". Nas duas seguradoras, nas
    #    duas redações. A âncora TEM de copiar o erro — `condom[íi]nio` casaria ZERO.
    {"step": "condominio_preambulo", "anchor": r"regras de condon[íi]mio preciso que informe",
     "reply": "", "noop": True, "notes": "📊 hdi 5 ses · yelum 1 ses."},
    {"step": "condominio_hora_inicial",
     "anchor": (r"hor[áa]rio inicial permitido para entrada do prestador|"
                r"a partir de qual hor[áa]rio o prestador de servi[çc]o pode entrar"),
     "reply": "{condominio_hora_inicial}", "fallback_adaptive": True,
     "notes": "📊 hdi 5 ses · yelum 1 ses."},
    {"step": "condominio_hora_final",
     "anchor": (r"hor[áa]rio final permitido para entrada do prestador|"
                r"at[ée] qual hor[áa]rio o prestador de servi[çc]o pode entrar"),
     "reply": "{condominio_hora_final}", "fallback_adaptive": True,
     "notes": "📊 hdi 5 ses · yelum 1 ses."},

    # ---- a chegada do prestador, e as orientacoes -------------------------
    # 🔴 ORDEM OBRIGATÓRIA: `chegada_prevista` vem ANTES de `senha_e_orientacoes`.
    #    Medido: a alternativa `pessoa maior de 18 anos` casa TAMBÉM a tela de
    #    chegada, que carrega DATA e PERÍODO. Âncora larga na frente = a tela que
    #    importa vira noop e o segurado não sabe quando o técnico vem.
    {"step": "chegada_prevista", "anchor": r"a chegada do prestador est[áa] (?:agendado|prevista)",
     "reply": "", "noop": True,
     "notes": "📊 1 tela em cada. 🔴 É a ÚNICA fonte de data/período no residencial "
              "da família. Vem ANTES de `senha_e_orientacoes` de propósito."},
    {"step": "senha_e_orientacoes",
     "anchor": (r"4 [úu]ltimos digitos do n[úu]mero informado|"
                r"senha para a visita t[ée]cnica corresponde|"
                r"4 d[íi]gitos finais\*? do n[úu]mero|pessoa maior de 18 anos"),
     "reply": "", "noop": True, "notes": "📊 yelum 5 telas / 11 ses · hdi 3 / 6."},
    {"step": "resumo_endereco_residencial",
     "anchor": (r"estamos prontos para seguir com a sua solicita[çc][ãa]o de "
                r"assist[êe]ncia 24 horas para o endere[çc]o"),
     "reply": "", "noop": True, "notes": "📊 yelum 3/3 · hdi 1/4."},
    {"step": "cardapio_de_servicos",
     "anchor": (r"voc[êe] consegue \*?solicitar ou acompanhar\*? os seguintes servi[çc]os|"
                r"voc[êe] pode solicitar ou acompanhar seus servi[çc]os conforme sua cobertura|"
                r"voc[êe] pode \*?acompanhar\*? todas as suas assist[êe]ncias"),
     "reply": "", "noop": True,
     "notes": "📊 hdi 3 telas / 6 ses · yelum 1 / 5. 🔴 O cardápio lista Ar condicionado, "
              "Dedetização e Eletroeletrônico — trabalhos SEM subserviço canônico. É "
              "informativo; declarar rótulo aqui seria criar tecla sem trabalho."},
    {"step": "telefone_invalido_familia", "anchor": r"o telefone informado n[ãa]o [ée] v[áa]lido",
     "reply": "{telefone_contato}", "requires": ["telefone_contato"],
     "notes": "📊 yelum 1/1 · hdi 1/2."},
]

# ---- o galho do PNEU: SEIS telas, e NENHUMA aceita resposta fixa ----------
# 🔴 Cada uma decide COBERTURA ou EQUIPAMENTO. "Mais de um pneu" muda o serviço
#    para GUINCHO; "sem estepe" idem; "lugar seguro" mexe na PRIORIDADE.
_FAMILIA_YH_PNEU = [
    {"step": "pneu_quantos", "anchor": r"quantos pneus foram furados",
     "reply": "{pneus_quantidade_opcao}", "requires": ["pneus_quantidade_opcao"],
     "fallback_adaptive": True, "only_subservices": ["pneu"],
     "notes": "📊 1-Apenas um 2-Mais de um. 🔴 'Mais de um pneu' muda o serviço para "
              "GUINCHO. Constante aqui manda borracheiro para carro que precisa de reboque."},
    {"step": "pneu_estepe", "anchor": r"voc[êe] possui um estepe",
     "reply": "{estepe_situacao}", "requires": ["estepe_situacao"],
     "fallback_adaptive": True, "only_subservices": ["pneu"],
     "notes": "📊 TRÊS opções, e NENHUMA é 'Sim': 1-Em condições 2-Sem condições 3-Não. "
              "As duas últimas levam a guincho."},
    {"step": "pneu_chave_macaco", "anchor": r"possui chave de roda e macaco",
     "reply": "{ferramentas_no_veiculo}", "requires": ["ferramentas_no_veiculo"],
     "fallback_adaptive": True, "only_subservices": ["pneu"], "notes": "📊 1/1 em cada."},
    {"step": "preambulo_lugar_seguro",
     "anchor": r"precisamos saber se voc[êe] est[áa] em um lugar seguro",
     "reply": "", "noop": True, "notes": "📊 é o ANÚNCIO; a pergunta vem depois."},
    {"step": "lugar_seguro",
     "anchor": (r"voc[êe] est[áa] em um lugar seguro\?|"
                r"o ve[íi]culo est[áa] em um local seguro"),
     "reply": "{local_seguro}", "requires": ["local_seguro"], "fallback_adaptive": True,
     "notes": "📊 2 telas em cada. 🔴 SEM reply fixo — a mesma razão escrita em "
              "`rb_InformacoesLocal`: responder 'Sim' por preguiça rebaixa, no escuro, "
              "a prioridade de quem está em perigo."},
    {"step": "pneu_regra_rodovia",
     "anchor": r"n[ãa]o conseguimos enviar o servi[çc]o de troca de pneus para rodovias",
     "reply": "", "noop": True, "only_subservices": ["pneu"],
     "notes": "📊 1/1. 🔴 É EXCLUSÃO, não aviso: em rodovia/marginal o pneu NÃO EXISTE "
              "nesta seguradora — é guincho. Vai a `regras_para_o_cliente`."},
]

# ---- o galho do GUINCHO ---------------------------------------------------
_FAMILIA_YH_GUINCHO = [
    {"step": "meio_de_transporte", "anchor": r"deseja solicitar o servi[çc]o de meio de transporte",
     "reply": "{meio_transporte_opcao}", "requires": ["meio_transporte_opcao"],
     "fallback_adaptive": True, "only_subservices": ["guincho"],
     "notes": "📊 yelum 4 ses · hdi 5 ses. 🔴 'Sim' ABRE UM SEGUNDO SERVIÇO (táxi) que "
              "o segurado não pediu — mas ele PODE ter direito e não saber. Vem do caso."},
    {"step": "destino_ja_tem", "anchor": r"j[áa] possui o endere[çc]o para onde devemos levar",
     "reply": "{tem_destino}", "fallback_adaptive": True, "only_subservices": ["guincho"],
     "notes": "📊 1+1 ses."},
    {"step": "destino_patio", "anchor": r"ser[áa] removido para o p[áa]tio do guincheiro",
     "reply": "", "noop": True, "only_subservices": ["guincho"],
     "notes": "🔴 O caso NÃO termina no protocolo: sobram 24 HORAS ÚTEIS para informar o "
              "destino, ou o carro fica no pátio. Vai a `expectativa_do_desfecho`."},
    {"step": "destino_cep", "anchor": r"para qual \*?cep\*? devemos levar o ve[íi]culo",
     "reply": "{destino_cep}", "fallback_adaptive": True, "notes": "📊 2+4 ses."},
    {"step": "origem_cep", "anchor": r"em qual \*?cep\*? o ve[íi]culo est[áa]",
     "reply": "{local_cep}", "fallback_adaptive": True, "notes": "📊 1+1 ses."},
    {"step": "endereco_livre_digitado",
     "anchor": (r"digite o endere[çc]o seguindo o exemplo|"
                r"me informe o \*?endere[çc]o completo\*?, seguindo o exemplo"),
     "reply": "{local_atual}", "fallback_adaptive": True, "notes": "📊 medido nas duas."},
    # 🔴 "confimar" — o erro de digitação é DA URA. Copiado do corpus.
    {"step": "confirmar_endereco_digitado",
     "anchor": r"poderia confimar o endere[çc]o|o endere[çc]o est[áa] correto\?",
     "reply": "Sim", "notes": "📊 hdi 2 telas. A URA escreve 'confimar', sem o R."},
    {"step": "compartilhe_localizacao", "anchor": r"compartilhe aqui sua localiza[çc][ãa]o",
     "reply": "", "noop": True,
     "notes": "📊 yelum 1. A URA pede o PIN nativo; o corredor não manda pin. A tela "
              "seguinte medida é 'Não foi possível localizar o endereço'."},
    {"step": "endereco_nao_localizado_familia", "anchor": r"n[ãa]o foi poss[íi]vel localizar o endere[çc]o",
     "reply": "", "noop": True, "notes": "📊 medido."},
]

# ---- o galho do CHAVEIRO (auto) -------------------------------------------
_FAMILIA_YH_CHAVEIRO = [
    {"step": "chave_o_que_aconteceu", "anchor": r"o que aconteceu com a chave",
     "reply": "{chave_problema}", "requires": ["chave_problema"], "fallback_adaptive": True,
     "only_subservices": ["chaveiro"],
     "notes": "📊 yelum 1 · hdi 1. Opções: Dentro do veículo / Perda / Quebrou / Outros."},
    {"step": "veiculo_trancado", "anchor": r"o ve[íi]culo est[áa] trancado",
     "reply": "{veiculo_trancado}", "fallback_adaptive": True, "only_subservices": ["chaveiro"],
     "notes": "📊 yelum 1."},
]

_FAMILIA_YH = (_FAMILIA_YH_TRONCO + _FAMILIA_YH_PNEU
               + _FAMILIA_YH_GUINCHO + _FAMILIA_YH_CHAVEIRO)

for _pb_yh in (YELUM_AUTO_WHATSAPP_V1, HDI_AUTO_WHATSAPP_V1,
               YELUM_RESIDENCIAL_WHATSAPP_V1, HDI_RESIDENCIAL_WHATSAPP_V1):
    _pb_yh["ura_steps"] = list(_pb_yh["ura_steps"]) + [dict(p) for p in _FAMILIA_YH]

# 🔴 AS DUAS TELAS QUE NUNCA PODEM VIRAR PASSO.
#    📊 yelum 2 telas / 2 ses · hdi 2 telas / 6 ses:
#       "Houve vítimas no local? Botão 1: Sim Botão 2: Não"
#       "A polícia foi acionada? Botão 1: Sim Botão 2: Não"
#    Elas só aparecem depois de "Houve uma colisão" — que é SINISTRO. E
#    `handoff_triggers` já tem `sinistro`, mas ele NÃO casa estas duas.
#    Um corredor que responde "Não" a "Houve vítimas?" com base num slot que
#    ninguém preencheu é a pior linha que este produto pode escrever.
#
#    E o RAMO DO CAMINHÃO (📊 8 telas / 2 sessões): tipo de caminhão, carroceria,
#    eixos, para-choque, acessórios, altura, comprimento. Esses oito campos
#    escolhem o EQUIPAMENTO DE REBOQUE (prancha, munck, cegonha) e o produto não
#    tem nenhum deles — nem a InfoCap tem altura de carroceria. Mesma regra do
#    `rb_NivelDaRua`: campo que escolhe equipamento não recebe chute.
for _pb_yh in (YELUM_AUTO_WHATSAPP_V1, HDI_AUTO_WHATSAPP_V1):
    _pb_yh["handoff_triggers"] = _pb_yh["handoff_triggers"] + [
        r"houve v[íi]timas no local", r"a pol[íi]cia foi acionada",
        r"tipo do caminh[ãa]o", r"tipo da carroceria", r"quantos eixos o caminh[ãa]o",
        r"tipo do para-?choque", r"altura\*? do caminh[ãa]o",
        r"comprimento\*? do caminh[ãa]o",
    ]


# ==========================================================================
# AZUL — TRONCO e GALHO (SPEC-084 BLOCO 1, 22/08/2026)
# ==========================================================================
#
# 🔴 A LIÇÃO QUE ORGANIZA ESTE BLOCO: **duas telas com contagem idêntica na
#    mesma seguradora não são dois sinais — são UMA tela.**
#    📊 O empate de 16 sessões (84,2%) medido na triagem — guincho = chaveiro =
#    vidro = martelinho = carro reserva — são os RÓTULOS do menu-raiz
#    "Selecione uma opção, por favor". Uma tela. Um sinal.
#    Por isso metade dos passos abaixo é `noop`: são CARDÁPIO, e a ESCOLHA vem
#    na bolha seguinte.
_AZUL_TRONCO = [
    {"step": "veiculo_por_placa", "anchor": r"voc[êe] quer atendimento para qual ve[íi]culo",
     "dynamic": "vehicle_by_plate", "reply": "{veiculo_opcao}", "fallback_adaptive": True,
     "notes": "📊 7 telas / 12 msgs / 11 sessões. Escolhe pela PLACA — '1' fixo pegou o "
              "carro ERRADO numa apólice com 2 veículos (teste Allianz 12/07)."},

    # ---- endereco: CINCO bolhas, UMA escolha ------------------------------
    {"step": "endereco_intro", "anchor": r"para informar o endere[çc]o, voc[êe] tem essas op[çc][õo]es",
     "reply": "", "noop": True, "notes": "📊 13 msgs / 8 sessões."},
    {"step": "endereco_compartilhe",
     "anchor": r"compartilhe a sua localiza[çc][ãa]o, selecionando o [íi]cone",
     "reply": "", "noop": True, "notes": "📊 13 msgs / 8 ses. A URA pede o PIN nativo."},
    {"step": "endereco_formulario", "anchor": r"se preferir, preencha o formul[áa]rio abaixo",
     "reply": "", "noop": True, "notes": "📊 18 msgs / 11 sessões."},
    {"step": "selecione_o_botao", "anchor": r"^selecione o bot[ãa]o:\s*$",
     "reply": "", "noop": True, "notes": "📊 18 msgs / 11 ses. Rótulo do botão do formulário."},
    # 🔴 O caso mais didático de CARDÁPIO x ESCOLHA da azul: 13 telas "distintas"
    #    na árvore que são UMA tela (muda só o endereço). A ESCOLHA é a bolha
    #    seguinte, "Está correto?", que `endereco_correto` já responde.
    #    Responder à primeira é responder à confirmação um passo antes dela.
    {"step": "localizei_o_endereco", "anchor": r"^localizei o endere[çc]o",
     "reply": "", "noop": True, "notes": "📊 13 telas -> 1 passo · 13 msgs / 7 sessões."},
    {"step": "falta_pouco_complemento", "anchor": r"falta pouco para finalizarmos essa etapa",
     "reply": "", "noop": True, "notes": "📊 12 msgs / 7 sessões."},
    {"step": "se_quiser_mudar_de_opcao", "anchor": r"se quiser mudar de op[çc][ãa]o, digite",
     "reply": "", "noop": True, "notes": "📊 14 msgs / 7 sessões."},
    {"step": "pedir_complemento", "anchor": r"digite ent[ãa]o um \*?complemento",
     "reply": "{endereco_complemento}", "fallback_adaptive": True,
     "notes": "📊 7 msgs / 7 ses. Default da própria URA: 'não tem'."},

    # ---- o guincho: destino, e o taxi que chega DEPOIS do protocolo -------
    {"step": "necessidade_guincho_lista",
     "anchor": r"selecione a op[çc][ãa]o que descreve melhor a sua necessidade",
     "reply": "Remoção de veículo", "only_subservices": ["guincho"],
     "notes": "📊 5 msgs / 5 ses. ⚠️ A 2ª opção é 'Envolvimento em acidente' — isso é "
              "SINISTRO, já coberto por `_AUTO_HANDOFF_TRIGGERS`. Quem pediu guincho "
              "por colisão não sai por esta porta."},
    {"step": "endereco_destino_intro", "anchor": r"vamos falar sobre o \*?endere[çc]o de destino",
     "reply": "", "noop": True, "only_subservices": ["guincho"],
     "notes": "📊 5 msgs / 5 ses. 🔴 É MARCA DE ESTADO: a bolha 'Digite o endereço "
              "completo' aparece DUAS vezes na mesma sessão (origem e destino), e esta "
              "é a única coisa que as separa. Ver PENDENCIAS."},
    {"step": "sabe_destino_guincho", "anchor": r"voc[êe] j[áa] sabe onde o guincho deve levar",
     "reply": "{tem_destino}", "fallback_adaptive": True, "only_subservices": ["guincho"],
     "notes": "📊 5 msgs / 5 sessões."},
    # 🔴 CHEGA DEPOIS DO PROTOCOLO: 📊 na sessão de 28/07/2026 o protocolo saiu às
    #    19:13:42 e o táxi às 19:13:44. "Sim" abre um SEGUNDO serviço no nome do
    #    segurado. "Não" é a única resposta segura sem pedido explícito.
    {"step": "taxi_junto",
     "anchor": (r"voc[êe] tamb[ée]m precisa solicitar um t[áa]xi|"
                r"voc[êe] precisa tamb[ée]m solicitar um t[áa]xi"),
     "reply": "Não", "notes": "📊 2 telas / 8 msgs / 7 sessões."},

    # ---- o galho do TECNICO: AGENDADO, nao "agora" ------------------------
    # 🔴 `tecnico` NÃO é subserviço declarado — `subservice_supported` devolve
    #    False e o caso vai a handoff. Os passos ficam registrados, não ligados.
    {"step": "tecnico_agendamento", "anchor": r"vou te ajudar com o agendamento de um t[ée]cnico",
     "reply": "", "noop": True, "notes": "📊 1 msg / 1 sessão. NÃO ESTABELECIDA."},
    {"step": "tecnico_data", "anchor": r"informe para quando voc[êe] quer agendar o servi[çc]o",
     "reply": "{data_agendamento}", "fallback_adaptive": True, "notes": "📊 1/1."},
    {"step": "tecnico_periodo", "anchor": r"qual per[íi]odo voc[êe] prefere",
     "reply": "{periodo_opcao}", "fallback_adaptive": True, "notes": "📊 1/1."},
    {"step": "tecnico_horario", "anchor": r"^e qual hor[áa]rio\?",
     "reply": "{horario_rotulo}", "fallback_adaptive": True, "notes": "📊 1/1."},

    # ---- DINHEIRO: nunca respondido automaticamente ------------------------
    # 🔴 O gêmeo azul da franquia da zurich. 📊 3 de 19 sessões chegaram aqui.
    {"step": "excedente_de_km", "anchor": r"superior ao limite de \d+ quil[ôo]metros",
     "reply": "", "noop": True,
     "notes": "📊 3 msgs / 3 sessões. 'o prestador poderá cobrar pelo excedente'. O "
              "texto vai ao dossiê; a tela seguinte ('Gostaria de continuar o "
              "agendamento?') é APROVAÇÃO, e está em `handoff_triggers`."},

    # ---- avisos e fim -----------------------------------------------------
    {"step": "aguarde_solicitando", "anchor": r"aguarde enquanto solicito o (?:seu )?servi[çc]o",
     "reply": "", "noop": True, "notes": "📊 2 telas / 11 msgs / 11 sessões."},
    {"step": "importante_18_anos", "anchor": r"[ée] necess[áa]rio ter algu[ée]m maior de 18 anos",
     "reply": "", "noop": True, "notes": "📊 3 telas / 10 msgs / 10 sessões."},
    {"step": "ainda_quer_continuar", "anchor": r"voc[êe] ainda quer continuar o seu atendimento",
     "reply": "Sim",
     "notes": "📊 8 msgs / 8 ses. 🔴 A resposta certa depende do run (com protocolo, "
              "'Sim' reabre conversa encerrada). O passo não vê o run — ver PENDENCIAS."},
    {"step": "avaliacao_convite", "anchor": r"a sua opini[ãa]o [ée] muito importante",
     "reply": "", "noop": True, "notes": "📊 2 telas / 8 msgs / 7 sessões."},
    # 🔴 "Não" NÃO É OPÇÃO DESTA TELA — 22/08/2026.
    #    📊 "Posso te ajudar com algo mais? Botão 1: Novo atendimento
    #        Botão 2: Falar com atendente  Botão 3: Encerrar"
    #    ⚠️ E "Falar com atendente" é a tecla que joga o caso no humano da
    #       SEGURADORA — o oposto do que esta SPEC quer. É o mesmo par de telas
    #       que a porto tem, e lá já está resolvido com dois passos.
    {"step": "encerrar_conversa_azul",
     "anchor": r"vou encerrar a conversa|quando precisar,? [ée] s[óo] chamar",
     "reply": "", "noop": True, "notes": "📊 7 telas -> 1 passo · 11 msgs / 11 sessões."},
    # 🔴 POR ULTIMO: alternativa larga emudece menu que o corredor sabe ler.
    {"step": "nao_entendi_azul",
     "anchor": (r"n[ãa]o entendi sua resposta|n[ãa]o entendi o que voc[êe] digitou|"
                r"ainda n[ãa]o consegui entender|"
                r"n[ãa]o entendi\. por favor, preciso que digite no formato"),
     "reply": "", "noop": True, "notes": "📊 5 telas / 7 msgs / 3 sessões."},
]
AZUL_AUTO_WHATSAPP_V1["ura_steps"] = (
    list(AZUL_AUTO_WHATSAPP_V1["ura_steps"]) + [dict(p) for p in _AZUL_TRONCO]
)
AZUL_AUTO_WHATSAPP_V1["handoff_triggers"] = AZUL_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    r"n[ãa]o consegui localizar o servi[çc]o sobre o qual",
    # 🔴 DINHEIRO: quem decide gastar o dinheiro do segurado é o segurado.
    r"gostaria de continuar o agendamento",
]

# ==========================================================================
# ZURICH — TRONCO, GALHO e FOLHA (SPEC-084 BLOCO 1, 22/08/2026)
# ==========================================================================
#
# 🔴 O ACHADO QUE REESCREVE O ENUNCIADO: a zurich NÃO é 89% vazia.
#    📊 Atribuindo cada tela órfã à sessão em que apareceu:
#       963f4097  107 telas EXCLUSIVAS -> SINISTRO DE COLISÃO
#       4118ba36   19 telas EXCLUSIVAS -> CONSULTAR PAGAMENTOS
#       d5ce1862   12 telas EXCLUSIVAS -> ACOMPANHAR PROCESSO
#       9f7dbd91 + 8e5fb8c0 -> ASSISTÊNCIA 24h  <- o corredor
#    **127 das 186 órfãs (68%) pertencem a três URAs que o corredor não faz.**
#    `sinistro` e `colisão` já são `handoff_triggers`; pagamento e
#    acompanhamento de processo não são subserviços.
#    📊 O buraco real da zurich é 59 telas, não 186.
_ZURICH_TRONCO = [
    {"step": "rodape_tirar_duvidas", "anchor": r"clique no bot[ãa]o \*?tirar d[úu]vidas",
     "reply": "", "noop": True, "notes": "📊 11 msgs / 9 sessões. Rodapé do cardápio."},
    {"step": "saudacao_laiz", "anchor": r"assistente virtual da zurich", "reply": "", "noop": True,
     "notes": "📊 2 telas / 9 msgs / 8 ses. 🔴 A redação estreita ('sou a assistente "
              "virtual') perderia a 2ª variante ('Eu sou a Laiz, assistente virtual')."},
    {"step": "optin_comunicacoes", "anchor": r"aceita receber comunica[çc][õo]es da zurich por esse canal",
     "reply": "Sim", "notes": "📊 1/1."},
    {"step": "optin_assistente", "anchor": r"deseja ser atendido pela laiz", "reply": "Sim",
     "notes": "📊 1/1."},
    {"step": "direcionar_menu", "anchor": r"vou direcionar voc[êe] para nosso menu principal",
     "reply": "", "noop": True, "notes": "📊 1/1."},
    {"step": "aviso_seguranca", "anchor": r"nunca compartilhe informa[çc][õo]es pessoais",
     "reply": "", "noop": True, "notes": "📊 6 msgs / 4 sessões."},
    {"step": "aviso_escopo_assist24h", "anchor": r"aqui voc[êe] vai \*?acionar a assist[êe]ncia 24h",
     "reply": "", "noop": True,
     "notes": "📊 5 msgs / 4 ses. CARDÁPIO: descreve o escopo. A escolha é 'Você deseja "
              "acionar a assistência 24h ou acionar o seguro?', que já tem passo."},
    {"step": "aviso_5_minutos", "anchor": r"responda a mensagem em at[ée] 5 minutos",
     "reply": "", "noop": True, "notes": "📊 2 msgs / 1 sessão."},
    {"step": "ainda_esta_por_ai", "anchor": r"voc[êe] ainda est[áa] por a[íi]", "reply": "Sim",
     "notes": "📊 2 telas / 6 msgs / 6 ses. 🔴 Mesma ressalva do `ainda_quer_continuar` "
              "da azul: sem ver o run, 'Sim' depois do protocolo reabre conversa "
              "encerrada. Ver PENDENCIAS."},

    # ---- o CARDAPIO do veiculo, e a ORDEM que se INVERTE -------------------
    # 🔴 📊 A ordem das duas telas SE INVERTE entre as sessões:
    #      9f7dbd91: pergunta -> lista      8e5fb8c0: lista -> pergunta
    #    Sem `noop` na lista, metade das sessões responde à tela errada.
    {"step": "lista_de_veiculos", "anchor": r"o ve[íi]culo encontrado com a placa digitada",
     "reply": "", "noop": True,
     "notes": "📊 3 msgs / 2 ses. CARDÁPIO. A escolha é 'Esse é o veículo que precisa "
              "de assistência? 1-Sim 2-Não'."},

    # ---- a arvore das PANES: onde guincho e bateria se separam ------------
    # 🔴 IDENTIFICADA, NÃO ESTABELECIDA (n = 1, sessão 9f7dbd91, 23/02/2026).
    #    Escrita mesmo assim porque o texto é literal e a alternativa é o cérebro
    #    adivinhar numa tela que escolhe EQUIPAMENTO.
    {"step": "sabe_o_que_ocorreu", "anchor": r"voc[êe] sabe o que ocorreu com o ve[íi]culo",
     "reply": "2", "only_subservices": ["guincho", "bateria"],
     "notes": "📊 1/1. 1-Não (PULA a desambiguação) 2-Sim. O corredor SABE — a atendente "
              "coletou `problema_descricao`. Responder 1 jogaria fora a informação que "
              "separa bateria de guincho."},
    {"step": "o_que_houve_panes",
     "anchor": r"o que houve\?[\s\S]{0,12}1\W{0,4}problema de bateria",
     "reply": "{pane_opcao}", "requires": ["pane_opcao"], "fallback_adaptive": True,
     "only_subservices": ["guincho", "bateria"],
     "notes": "📊 1/1. 1=BATERIA 2=partida 4=câmbio 6=motor 10=alternador. 🔴 SEM reply "
              "fixo: `subservice_menu_map` manda 4 (Panes) para guincho E bateria; é "
              "ESTA tela que separa. ⚠️ `[\\s\\S]{0,12}` e não `.{0,12}` — a URA quebra "
              "linha depois do '?'."},
    {"step": "tipo_cambio", "anchor": r"qual [ée] o tipo de c[âa]mbio",
     "reply": "{cambio_opcao}", "requires": ["cambio_opcao"], "fallback_adaptive": True,
     "notes": "📊 1/1. 1-Manual 2-Automático. SEM default: automático travado exige "
              "PRANCHA, manual não."},
    {"step": "alavanca_travada", "anchor": r"a alavanca est[áa] travada",
     "reply": "{alavanca_travada_opcao}", "requires": ["alavanca_travada_opcao"],
     "fallback_adaptive": True, "notes": "📊 1/1. SEM default: decide o EQUIPAMENTO."},

    # ---- o galho do PNEU ---------------------------------------------------
    {"step": "veiculo_blindado", "anchor": r"o ve[íi]culo [ée] blindado", "reply": "2",
     "fallback_adaptive": True, "notes": "📊 1/1. Default Não; blindado muda o guincho."},
    {"step": "mais_de_um_pneu", "anchor": r"mais de 1 pneu est[áa] danificado",
     "reply": "{pneus_danificados_opcao}", "requires": ["pneus_danificados_opcao"],
     "fallback_adaptive": True, "only_subservices": ["pneu"],
     "notes": "📊 1/1. 🔴 SEM default: 'Sim' vira guincho, 'Não' vira borracheiro."},
    {"step": "tem_estepe", "anchor": r"possui estepe, macaco e chave de rodas",
     "reply": "{estepe_opcao}", "requires": ["estepe_opcao"], "fallback_adaptive": True,
     "only_subservices": ["pneu"],
     "notes": "📊 1/1. 🔴 SEM default: sem estepe não há troca, há reboque."},
    {"step": "lugar_seguro_zurich", "anchor": r"voc[êe] est[áa] em um lugar seguro",
     "reply": "{local_seguro_opcao}", "requires": ["local_seguro_opcao"],
     "fallback_adaptive": True,
     "notes": "📊 1/1. 🔴 SEM default — responder 'seguro' por preguiça rebaixa, no "
              "escuro, a prioridade de quem está parado num lugar perigoso."},

    # ---- o endereco MANUAL (quando o geocode falha): 9 elos ---------------
    # 🔴 `endereco_detalhado` já responde "1" para ENTRAR neste ramo, e nenhum dos
    #    8 passos seguintes existia. Cada elo sem passo custa ~14s numa URA que
    #    declara encerrar por inatividade em 5 minutos.
    {"step": "endereco_nao_identificado",
     "anchor": r"n[ãa]o identifiquei um endere[çc]o a partir da sua localiza[çc][ãa]o",
     "reply": "", "noop": True, "notes": "📊 1/1."},
    {"step": "preciso_de_informacoes", "anchor": r"okay! preciso de algumas informa[çc][õo]es",
     "reply": "", "noop": True, "notes": "📊 1/1."},
    {"step": "pedir_cep_zurich", "anchor": r"me informe seu cep",
     "reply": "{endereco_cep}", "fallback_adaptive": True, "notes": "📊 1/1."},
    {"step": "pedir_rua", "anchor": r"qual o nome da rua",
     "reply": "{endereco_rua}", "fallback_adaptive": True, "notes": "📊 1/1."},
    {"step": "pedir_numero_endereco", "anchor": r"qual o n[úu]mero do endere[çc]o que voc[êe] est[áa]",
     "reply": "{endereco_numero}", "fallback_adaptive": True, "notes": "📊 1/1."},
    # 🔴 `^` OBRIGATÓRIO: sem ele `qual o bairro` casaria "Em qual *bairro*
    #    ocorreu?" do fluxo de SINISTRO, que vive no mesmo playbook.
    #    Medido: com `^`, 1 tela cada; sem `^`, 2.
    {"step": "pedir_bairro", "anchor": r"^\s*qual o bairro",
     "reply": "{endereco_bairro}", "fallback_adaptive": True, "notes": "📊 1/1."},
    {"step": "pedir_cidade", "anchor": r"e a cidade, qual [ée]",
     "reply": "{endereco_cidade}", "fallback_adaptive": True, "notes": "📊 1/1."},
    {"step": "pedir_estado", "anchor": r"^\s*qual o estado",
     "reply": "{endereco_uf}", "fallback_adaptive": True, "notes": "📊 1/1."},
    {"step": "resumo_do_endereco", "anchor": r"segue o resumo dos dados informados",
     "reply": "", "noop": True,
     "notes": "📊 1/1. CARDÁPIO: a escolha é 'Os dados estão corretos?', que já tem passo."},

    # ---- o DESFECHO --------------------------------------------------------
    {"step": "endereco_para_solicitar", "anchor": r"vamos solicitar sua assistencia para o endere[çc]o",
     "reply": "", "noop": True,
     "notes": "📊 2 telas / 2 ses. CARDÁPIO: a escolha é 'Podemos confirmar a "
              "solicitação? 1-Sim 2-Alterar endereço'."},
    {"step": "aguarde_finalizando", "anchor": r"estamos finalizando sua solicita[çc][ãa]o",
     "reply": "", "noop": True, "notes": "📊 2/2."},
    {"step": "assistencia_solicitada_zurich", "anchor": r"sua assist[êe]ncia foi solicitada",
     "reply": "", "noop": True, "notes": "📊 2/2. É o DESFECHO; quem lê o número é `protocol`."},
    {"step": "chegada_prevista_zurich", "anchor": r"chegada do profissional prevista para o dia",
     "reply": "", "noop": True,
     "notes": "📊 2/2. 🔴 A zurich promete DATA e HORA ('prevista para o dia DD/MM às "
              "HH:MM'), não 'em N minutos'. Vai a `expectativa_do_desfecho`."},
    {"step": "telefones_acompanhamento", "anchor": r"para acompanhar o status da assist[êe]ncia 24h",
     "reply": "", "noop": True, "notes": "📊 2/2. 0800 729 1400 · +55 11 4133 6932."},
    {"step": "como_continuar_agora", "anchor": r"como voc[êe] quer continuar agora",
     "reply": "Encerrar atendimento", "notes": "📊 2/2."},
    {"step": "pesquisa_convite", "anchor": r"responda a pesquisa a seguir", "reply": "", "noop": True,
     "notes": "📊 5 msgs / 3 sessões."},
    {"step": "pesquisa_nps", "anchor": r"o quanto voc[êe] recomenda o chat da zurich",
     "reply": "", "noop": True, "notes": "📊 8 msgs / 3 sessões."},
    {"step": "encerramento_zurich",
     "anchor": r"vou encerrar (?:nosso|seu) atendimento|encerro seu atendimento por aqui",
     "reply": "", "noop": True, "notes": "📊 2 telas / 10 msgs / 9 sessões."},
    {"step": "nao_entendi_opcao",
     "anchor": (r"n[ãa]o entendi a op[çc][ãa]o escolhida|"
                r"ainda n[ãa]o entendi o que voc[êe] (?:digitou|escolheu)|"
                r"poxa, n[ãa]o entendi"),
     "reply": "", "noop": True, "notes": "📊 4 telas / 7 msgs / 5 sessões."},
]
ZURICH_AUTO_WHATSAPP_V1["ura_steps"] = (
    list(ZURICH_AUTO_WHATSAPP_V1["ura_steps"]) + [dict(p) for p in _ZURICH_TRONCO]
)

# 🔴 O QUE **NÃO** VIRA PASSO NA ZURICH — e a razão de cada um.
ZURICH_AUTO_WHATSAPP_V1["handoff_triggers"] = ZURICH_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    # 📊 2 telas / 4 msgs / 3 sessões. Quando a URA chega aqui o corredor já
    #    errou TRÊS respostas. Responder mais uma vez é insistir.
    r"continuo sem entender",
    # 📊 4 msgs / 3 sessões. É a porta do fluxo de SINISTRO.
    r"escolha o servi[çc]o que deseja acessar",
    # 🔴 DINHEIRO. 📊 "*Franquia*: R$ 18.189,16" seguida de "Podemos continuar com
    #    o serviço?". Aceitar um custo em nome do segurado é decisão comercial
    #    DELE. A parada tem de ser explícita, e o valor vai ao dossiê.
    r"verifique as informa[çc][õo]es do seguro[\s\S]{0,80}franquia",
]

# 🔴 O NÚMERO DO PROCESSO NÃO É PROTOCOLO DE ASSISTÊNCIA.
#    📊 "*Número do processo:* 31.26.333122.01" é o número do SINISTRO. Pô-lo em
#    `protocol` faria o corredor de assistência encerrar um caso com o número de
#    um processo de colisão. Âncora própria, usada só no dossiê do handoff.
#    CONTROLE: o grupo aceita PONTO — que é o que uma âncora de dígitos
#    contíguos perderia — e NÃO casa "Qual é o número do processo?" (sem dígitos).
ZURICH_AUTO_WHATSAPP_V1["capture_anchors"] = {
    **ZURICH_AUTO_WHATSAPP_V1["capture_anchors"],
    "processo_sinistro": r"n[úu]mero do processo:?\s*\*?(\d{2}\.\d{2}\.\d{4,8}\.\d{2})",
}


# ==========================================================================
# BRADESCO — a ESCADA DE ENDERECO, e ela e pedida DUAS vezes
# ==========================================================================
#
# 📊 A URA do bradesco não aceita endereço livre: pede degrau a degrau, e pede
#    DUAS escadas (origem e destino). O par CIDADE parecia inseparável e não é —
#    🔴 **a vírgula depois de "Agora" separa as duas com 100% de precisão**:
#
#      origem : "AGORA, o nome da *cidade*. Exemplos:..."     (com vírgula)
#      destino: "Ok, AGORA o nome da *cidade*. Exemplo:..."   (sem vírgula)
#
#    As duas âncoras são DISJUNTAS, e por isso não dependem da ordem da lista.
#
# ⚠️ `inject_address_slots` já deriva `local_uf/cidade/rua/numero` e `destino_*`
#    de `local_atual`/`local_destino`. **Nenhum slot novo é preciso.**
_BRADESCO_ENDERECO = [
    {"step": "local_uf", "anchor": r"nome do estado, onde seu ve[íi]culo est[áa]",
     "reply": "{local_uf}", "fallback_adaptive": True, "notes": "📊 1 tela / 3 sessões."},
    {"step": "local_cidade", "anchor": r"agora, o nome da cidade",
     "reply": "{local_cidade}", "fallback_adaptive": True,
     "notes": "📊 1 tela / 3 ses. 🔴 A VÍRGULA É A ÂNCORA."},
    {"step": "local_rua", "anchor": r"agora preciso do nome da rua",
     "reply": "{local_rua}", "fallback_adaptive": True, "notes": "📊 1 tela / 4 sessões."},
    {"step": "local_numero", "anchor": r"n[úu]mero mais pr[óo]ximo, de onde seu ve[íi]culo",
     "reply": "{local_numero}", "fallback_adaptive": True,
     "notes": "📊 2 telas / 3 ses — cobre 'vai estar?' e 'está' com uma âncora só."},
    {"step": "ponto_referencia_bradesco", "anchor": r"me informa um ponto de refer[êe]ncia",
     "reply": "{ponto_referencia}", "fallback_adaptive": True,
     "notes": "📊 1 tela / 4 ses. Se não houver, 'não tem'."},
    {"step": "destino_uf", "anchor": r"nome do estado, pra onde voc[êe] quer levar",
     "reply": "{destino_uf}", "fallback_adaptive": True, "only_subservices": ["guincho"],
     "notes": "📊 1 tela / 4 sessões."},
    {"step": "destino_cidade", "anchor": r"ok, agora o nome da cidade",
     "reply": "{destino_cidade}", "fallback_adaptive": True, "only_subservices": ["guincho"],
     "notes": "📊 1 tela / 4 ses. 🔴 SEM vírgula depois de 'agora' — é o destino."},
    {"step": "destino_numero", "anchor": r"informa o n[úu]mero,\s*de onde voc[êe] quer levar",
     "reply": "{destino_numero}", "fallback_adaptive": True, "only_subservices": ["guincho"],
     "notes": "📊 1 tela / 4 ses. A VÍRGULA de novo: 'o *número*,' (destino) vs "
              "'o *número* mais próximo' (origem). `\\s*` porque `_norm` não colapsa espaço."},
]
_BRADESCO_TRONCO = [
    # ---- agendamento: ANTES do noop, porque a 2a redacao comeca com "Nao entendi!"
    {"step": "agendamento_dia", "anchor": r"qual dia voc[êe] prefere fazer o agendamento",
     "reply": "Hoje",
     "notes": "📊 2 telas / 2 ses. 🔴 TEM de vir ANTES do noop: a 2ª redação começa com "
              "'Não entendi!', que o noop também casa. Se o noop viesse antes, o corredor "
              "ficaria MUDO diante de um menu que sabe responder, e a URA encerraria por "
              "inatividade."},
    {"step": "agendamento_hora_bradesco", "anchor": r"qual o melhor hor[áa]rio",
     "reply": "{hora_agendamento}", "fallback_adaptive": True,
     "notes": "📊 1 tela / 2 ses. Formato ESTRITO HH:MM 24h."},
    {"step": "agendamento_confirma", "anchor": r"quer agendar a assist[êe]ncia pra",
     "reply": "Confirmar",
     "notes": "📊 2 telas / 2 ses. 🔴 A âncora para ANTES da hora, que é dinâmica — uma "
              "âncora com '14h00' casaria 1 tela e morreria amanhã."},
    {"step": "agendamento_minimo_2h", "anchor": r"agendamento para um per[íi]odo inferior a duas horas",
     "reply": "Sim",
     "notes": "📊 1/1. 🔴 REGRA DA SEGURADORA: agendamento mínimo 2h de antecedência. "
              "Vai a `regras_para_o_cliente` — o cliente precisa ouvir isso ANTES."},

    # ---- veiculo e endereco -----------------------------------------------
    {"step": "endereco_confirma_bradesco",
     "anchor": r"j[áa] consegui te localizar[\s\S]{0,120}endere[çc]o est[áa] correto",
     "reply": "Sim",
     "notes": "📊 1/1. ⚠️ `[\\s\\S]{0,120}` — a tela tem 3 quebras e `.` não casa `\\n`."},
    {"step": "rodas_travadas", "anchor": r"rodas est[ãa]o travadas", "reply": "Não",
     "notes": "📊 1 tela / 2 ses. ⚠️ A âncora da família Allianz (`rodas? travadas?`) é "
              "larga demais para importar: casaria a tela da HDI que lista várias "
              "condições ao mesmo tempo."},
    {"step": "placa_nao_encontrada", "anchor": r"n[ãa]o encontrei esta placa no meu sistema",
     "reply": "{veiculo_placa}", "requires": ["veiculo_placa"],
     "notes": "📊 1/1. 🔴 UMA repetição, não duas: a 2ª falha leva a 'Por este canal não "
              "podemos seguir', que é handoff."},
    {"step": "reentrada_confirma_veiculo",
     "anchor": (r"vou continuar seu atendimento aqui no whatsapp[\s\S]{0,200}"
                r"as informa[çc][õo]es est[ãa]o corretas"),
     "reply": "Sim", "dynamic": "vehicle_by_plate", "fallback_adaptive": True,
     "notes": "📊 1/1. 🔴 Esta tela DISPARAVA o freio (`as informações estão corretas`) "
              "no turno 28/28 — e ela é REENTRADA, não confirmação final."},
    {"step": "desfecho_sem_numero",
     "anchor": (r"o agendamento t[áa] confirmado|"
                r"logo mais, a sua assist[êe]ncia j[áa] ser[áa] acionada"),
     "reply": "", "noop": True,
     "notes": "📊 2 telas / 3 sessões. 🔴 A ARMADILHA CONFIRMADA: `app.europ.com.br` "
              "sozinho casaria 4 telas em 4 sessões e só 2 são desfecho — as outras são "
              "'Por este canal não podemos seguir' e 'encerrando por falta de interação'. "
              "A âncora NÃO usa o domínio."},

    # ---- o noop largo, POR ULTIMO ------------------------------------------
    # ⚠️ A tela "1. Toque em Enviar Localização. 2. Escolha..." tem "1." e "2." e
    #    NÃO é menu. Só o noop impede o cérebro de responder "1".
    {"step": "avisos_informativos_bradesco",
     "anchor": (r"cad[êe] voc[êe]\? vou encerrar seu atendimento|ainda n[ãa]o entendi|"
                r"n[ãa]o entendi!|obrigado por entrar em contato conosco|"
                r"aguarde um momento enquanto aciono meu sistema|"
                r"ainda n[ãa]o consegui te localizar|toque em enviar localiza[çc][ãa]o|"
                r"jeito mais f[áa]cil de me ajudar a te encontrar|como foi o servi[çc]o de"),
     "reply": "", "noop": True, "notes": "📊 12 telas / 5 sessões."},
]
BRADESCO_AUTO_WHATSAPP_V1["ura_steps"] = (
    list(BRADESCO_AUTO_WHATSAPP_V1["ura_steps"])
    + [dict(p) for p in _BRADESCO_ENDERECO + _BRADESCO_TRONCO]
)
# 📊 3 sessões de 6. O gatilho declarado hoje pega só a primeira das três.
BRADESCO_AUTO_WHATSAPP_V1["handoff_triggers"] = BRADESCO_AUTO_WHATSAPP_V1["handoff_triggers"] + [
    r"estamos com problemas para continuar seu atendimento",
    r"encerrando este atendimento por falta de intera[çc][ãa]o",
]

# ==========================================================================
# MAPFRE — 📊 ZERO de 6 sessoes abriram assistencia
# ==========================================================================
#
# 🔴 E o achado estrutural: **são DOIS bots, não um.**
#      BOT DO SEGURADO  -> a tecla se chama "Assistência 24H"
#      BOT DO CORRETOR  -> a tecla se chama "Assistência"   (entra por código)
#    `subservice_menu_map` declara o primeiro para as 4 rotas. Para qual dos
#    dois a corretora escreve **não está no acervo** — ver PENDENCIAS.
_MAPFRE_TRONCO = [
    # 🔴 O CONTROLE QUE IMPORTA: a âncora ingênua `sobre qual assunto você quer
    #    falar` casava 2 telas — roubava o menu do CORRETOR, que tem OUTRAS
    #    opções. `[\s\S]{0,60}` porque `.` NÃO casa `\n` em Python.
    {"step": "menu_assunto_veiculo",
     "anchor": r"no atendimento de seguros para ve[íi]culos[\s\S]{0,60}sobre qual assunto",
     "reply": "{assunto_opcao}", "requires": ["assunto_opcao"], "fallback_adaptive": True,
     "notes": "📊 1 tela / 3 sessões. LISTA (rótulo). ⚠️ A máscara do corpus comeu o "
              "'24H' do rótulo — conferir a grafia na tela real antes de fixar."},
    {"step": "menu_assunto_corretor", "anchor": r"escolher sobre qual assunto voc[êe] quer falar",
     "reply": "Assistência",
     "notes": "📊 1 tela / 1 sessão. Canal do CORRETOR. 🔴 Rótulo DIFERENTE do bot do "
              "segurado — SEM '24H'. Tecla errada = assunto errado."},
    {"step": "codigo_corretor", "anchor": r"digite o seu c[óo]digo de corretor",
     "reply": "{codigo_corretor}", "requires": ["codigo_corretor"], "fallback_adaptive": True,
     "notes": "📊 1/1. 🔴 SLOT NOVO, e é PENDÊNCIA DE CONFIGURAÇÃO da corretora, não de "
              "coleta do segurado. Sem ele o canal do corretor não abre."},
    {"step": "perfil_segurado",
     "anchor": r"voc[êe] [ée] segurado ou terceiro|em qual perfil voc[êe] se encaixa",
     "reply": "Segurado", "notes": "📊 2 telas / 2 sessões."},
    {"step": "protocolo_agiliza", "anchor": r"voc[êe] j[áa] possui um protocolo aberto pelo",
     "reply": "Não", "notes": "📊 1/1."},
    {"step": "algo_mais_mapfre", "anchor": r"posso te ajudar em algo mais", "reply": "Não",
     "notes": "📊 1 tela / 2 ses. ⚠️ Na TOKIO a MESMA pergunta tem outros rótulos "
              "('Outro serviço/Menu inicial/Encerrar'). Duas seguradoras, duas respostas."},
    {"step": "deflexao_portal",
     "anchor": (r"portal do cliente mapfre|clique no link e fale com nosso agente conversacional|"
                r"preencher o formul[áa]rio pelo link|por qual canal voc[êe] deseja seguir|"
                r"comunique seu sinistro de forma r[áa]pida"),
     "reply": "", "noop": True,
     "notes": "📊 5 telas. Todas do galho SINISTRO: a mapfre deflexiona sinistro para o "
              "portal. É DESFECHO_NEGATIVO deste canal, não assistência."},
    {"step": "pesquisa_satisfacao_mapfre",
     "anchor": (r"grau de satisfa[çc][ãa]o com o atendimento|"
                r"principal motivo para voc[êe] dar essa nota|"
                r"acompanhamento da sua solicita[çc][ãa]o est[áa] sendo satisfat[óo]rio|"
                r"voc[êe] conseguiu fazer o que precisava|"
                r"voc[êe] conseguiu comunicar o seu sinistro"),
     "reply": "", "noop": True, "notes": "📊 5 telas / 2 sessões."},
    # 🔴 O noop largo, POR ÚLTIMO — e o que EU TIREI dele, medido:
    #    a alternativa `voc[êe] est[áa] no atendimento de` ROUBAVA o menu de
    #    assunto (a tela que abre as 4 rotas). Removida.
    #    **Prova de que "noop por último" não basta sozinho: uma alternativa
    #    larga demais precisa SAIR, não só descer na lista.**
    {"step": "avisos_informativos_mapfre",
     "anchor": (r"respeita e cumpre as exig[êe]ncias previstas na|"
                r"l[íi]ngua brasileira de sinais|"
                r"pode digitar sair (?:a qualquer momento )?para encerrar|"
                r"aguardo sua reposta para continuar|"
                r"nossa conversa ser[áa] encerrada em alguns minutos|"
                r"agradece o seu contato|vamos seguir com o seu atendimento agora|"
                r"obrigado pelas informa[çc][õo]es|que bom falar com voc[êe]|"
                r"estou aqui pra te ajudar|pronto, voc[êe] est[áa] na [áa]rea de|"
                r"em at[ée] 24 horas [úu]teis seu sinistro|"
                r"em caso de d[úu]vidas voc[êe] pode entrar em contato|"
                r"a vistoria no ve[íi]culo|obrigada pela confirma[çc][ãa]o|"
                r"quando precisar de ajuda sobre seu processo|"
                r"basta iniciar uma conversa e selecionar|"
                r"estamos sempre [àa] disposi[çc][ãa]o|"
                r"o n[úu]mero de protocolo para este atendimento"),
     "reply": "", "noop": True,
     "notes": "📊 15 telas / 5 sessões. ⚠️ 'O número de protocolo para este atendimento' "
              "é do CARRO RESERVA e vem antes da transferência humana — é carimbo de "
              "atendimento, não número de serviço."},
]
MAPFRE_AUTO_WHATSAPP_V1["ura_steps"] = (
    list(MAPFRE_AUTO_WHATSAPP_V1["ura_steps"]) + [dict(p) for p in _MAPFRE_TRONCO]
)

# ==========================================================================
# ALFA — 🔴 10 das 18 orfas sao telas da ALLIANZ, PALAVRA POR PALAVRA
# ==========================================================================
#
# `ALFA_AUTO_WHATSAPP_V1` faz `[dict(s) for s in _ALLIANZ_FAMILY_AUTO_STEPS]`.
# 📊 Comparando `_norm` de toda tela alfa contra toda tela allianz: 10 das 18
#    órfãs são idênticas. **Escrever esses 10 na FAMÍLIA paga alfa e allianz na
#    mesma edição.** Escrevê-los na alfa cria a segunda cópia — e é assim que
#    nasce o `cpf_anterior` corrigido de um lado e vencido do outro.
_ALFA_ALLIANZ_FAMILIA = [
    # ⚠️ A URA NÃO NUMERA A PRIMEIRA OPÇÃO, e o conferidor pegou isso:
    #    📊 "Ok, agora selecione o endereço onde está o veículo:
    #        *{ENDERECO}
    #        *2 -* Outra localização. *Compartilhar via Whatsapp*"
    #    Só o `2` aparece marcado. O `1` é o endereço da apólice, escrito sem
    #    número — e responder "1" é o que a sessão real fez, com sucesso.
    #    🔴 É formatação quebrada DA SEGURADORA, não do corredor. Fica declarado
    #       para que ninguém "conserte" isto trocando por "2".
    {"step": "selecionar_endereco_veiculo", "anchor": r"selecione o endere[çc]o onde est[áa] o ve[íi]culo",
     "reply": "1", "fallback_adaptive": True,
     "constante_justificada": (
         "📊 A URA escreve a opção 1 SEM número (só o endereço, com asterisco) e "
         "numera apenas a 2. '1' é o endereço da apólice, e foi o que as 3 sessões "
         "medidas responderam. Com `fallback_adaptive`, se o local do caso for outro, "
         "o cérebro assume."),
     "notes": "📊 3 sessões. 1 = o endereço da apólice; 2 = outra localização. Se o local "
              "do caso for outro, o adaptativo assume."},
    {"step": "endereco_confirma_alfa", "anchor": r"o endere[çc]o [ée]:[\s\S]{0,140}confirma",
     "reply": "1",
     "notes": "📊 2 telas / 2 ses. ⚠️ `[\\s\\S]{0,140}` porque `.` não casa `\\n` e o "
              "endereço fica entre as duas frases. ⚠️ A ALLIANZ tem uma 3ª variante "
              "('*3 -* Alterar número') — o passo tolera sem responder '3'."},
    {"step": "servico_complementar", "anchor": r"precisa de algum servi[çc]o complementar",
     "reply": "2",
     "notes": "📊 2 sessões. 2 = Não. O corredor abre O QUE o cliente pediu, um por vez."},
    {"step": "confirmar_numero_endereco", "anchor": r"precisamos confirmar o n[úu]mero do endere[çc]o",
     "reply": "{local_numero}", "fallback_adaptive": True, "notes": "📊 1 sessão."},
    # ---- o galho do PNEU: as duas telas que decidem COBERTURA -------------
    {"step": "pneus_furados", "anchor": r"quantos pneus furaram",
     "reply": "{pneus_furados_opcao}", "requires": ["pneus_furados_opcao"],
     "fallback_adaptive": True, "only_subservices": ["pneu"],
     "notes": "📊 1/1. 🔴 SEM reply fixo — a tecla errada abre o chamado errado."},
    {"step": "equipamentos_troca", "anchor": r"equipamentos para troca \(chave de roda",
     "reply": "{equipamentos_troca_opcao}", "requires": ["equipamentos_troca_opcao"],
     "fallback_adaptive": True, "only_subservices": ["pneu"],
     "notes": "📊 1/1. 🔴 TAMBÉM sem reply fixo: '2' (não tem step) muda o serviço de "
              "borracheiro para REBOQUE. É pergunta de cobertura disfarçada de sim/não."},
    # ---- desfecho e avisos -------------------------------------------------
    {"step": "desfecho_protocolo_alfa", "anchor": r"protocolo:\s*\d|receber[áa] um link por sms",
     "reply": "", "noop": True,
     "notes": "📊 3 telas / 3 sessões. `_ANCORA_DE_PROTOCOLO` já captura os três "
              "(50274607, 51314713, 52675121); o passo é só para o motor não responder."},
    # 🔴 UM DESFECHO_NEGATIVO NÃO PODE DIVIDIR PASSO COM "aguarde em local seguro":
    #    um encerra o caso, o outro manda ficar calado. Por isso ele é separado.
    {"step": "central_sem_atendimento", "anchor": r"no momento eu n[ãa]o consigo te ajudar",
     "reply": "", "noop": True,
     "notes": "📊 1 tela / 3 sessões, todas de guincho. Já é `handoff_trigger` declarado; "
              "o passo existe porque handoff e passo são mecanismos separados e a tela "
              "continuava órfã. 📊 `zonas_do_acervo` registra o mesmo, de outra medição: "
              "'NÃO é fronteira: é ABANDONO PARA TELEFONE — um DESFECHO_NEGATIVO'."},
    {"step": "avisos_informativos_familia",
     "anchor": (r"faremos o poss[íi]vel para que o profissional chegue|"
                r"respons[áa]vel maior de 18 anos esteja no local|"
                r"sua assist[êe]ncia foi confirmada|"
                r"siga o passo a passo a seguir de acordo com seu aparelho|"
                r"obrigado por entrar em contato!"),
     "reply": "", "noop": True, "notes": "📊 5 telas / 4 sessões."},
]
# 🔴 NA FAMÍLIA, não na alfa: paga as duas seguradoras de uma vez.
_ALLIANZ_FAMILY_AUTO_STEPS.extend(dict(p) for p in _ALFA_ALLIANZ_FAMILIA)
for _pb_fam in (ALFA_AUTO_WHATSAPP_V1, ALLIANZ_AUTO_WHATSAPP_V1):
    _pb_fam["ura_steps"] = list(_pb_fam["ura_steps"]) + [dict(p) for p in _ALFA_ALLIANZ_FAMILIA]


# ==========================================================================
# ALLIANZ — TRONCO e GALHO (SPEC-084 BLOCO 1, 22/08/2026)
# ==========================================================================
#
# ⚠️ A ÓRFÃ Nº 1 DAS DUAS ROTAS **NÃO ENTRA AQUI**, e é a de maior retorno:
#    📊 "Vou transferir seu caso para um especialista" — retorno 496 no
#    residencial (31 sessões) e 66 no auto (11). Ela é **FRONTEIRA**: já é
#    `pausar_e_chamar`, e transformá-la em passo seria escrever um corredor
#    para a tela que ENTREGA o atendimento ao humano.
#    A `arvore.py` já a exclui da fila; a bancada de controle não, porque só
#    consulta `match_ura_step`. É viés do medidor, não dívida do corredor.
_ALLIANZ_RESID_TRONCO = [
    # ---- 🔴 O MENU QUE NOMEIA OS SERVICOS QUE O CODIGO NAO TEM -----------
    # 📊 2 telas / 21 sessões — a maior órfã REAL do residencial.
    #    "*1 -* Dedetização *2 -* Limpeza do Imóvel *3 -* Limpeza de Caixa
    #     d'Água *4 -* Ar-condicionado *5 -* Consulta veterinária ..."
    # ⚠️ A resposta vem do CASO. Fixar uma tecla aqui escolheria o serviço
    #    do segurado por ele — o mesmo defeito do `menu_qual_seguro`.
    {"step": "menu_outros_servicos_residencia", "anchor": r"qual desses servi[çc]os,? voc[êe] precisa",
     "reply": "{outro_servico_opcao}", "requires": ["outro_servico_opcao"],
     "fallback_adaptive": True,
     "notes": "📊 2 telas / 21 sessões. 🔴 É o menu que NOMEIA os serviços que o produto "
              "ainda não declara (dedetização, limpeza de caixa d'água, ar-condicionado, "
              "consulta veterinária). Ver PENDENCIAS: cada um precisa de subserviço "
              "canônico antes de virar rota."},

    # ---- 🔴 A MAIOR FAMILIA ORFA: a lista de enderecos da apolice --------
    # 📊 17 telas distintas / 34 sessões. São 17 textos porque o ENDEREÇO muda;
    #    é UM passo. A forma é sempre "*1 -* <endereço> *2 -* Voltar *3 -* Sair".
    # 🔴 CONTROLE: a âncora exige as TRÊS marcas (o `1 -` no início, o `2 - Voltar`
    #    e o `3 - Sair`). Medido: 17 telas, e ROUBA ZERO de outro passo.
    {"step": "escolher_endereco_da_lista",
     "anchor": r"^\*?1\s*-\*?\s[\s\S]{0,180}\*?2\s*-\*?\s*voltar[\s\S]{0,24}\*?3\s*-\*?\s*sair",
     "reply": "1", "fallback_adaptive": True,
     "notes": "📊 17 telas / 34 sessões — a maior família órfã do corredor. '1' é o "
              "endereço da apólice. ⚠️ Se o caso trouxer outro endereço, o adaptativo "
              "assume: escolher às cegas manda o prestador para a casa errada."},

    # ---- o galho do CONDOMINIO: 5 sessoes, e o produto nao o conhecia -----
    # 🔴 Só se chega aqui respondendo **2** em `menu_qual_seguro_tres_opcoes` —
    #    a tela que até 22/08/2026 era respondida com "1" fixo. Consertada ela,
    #    este galho passa a existir de verdade.
    {"step": "cnpj_condominio", "anchor": r"digite o \*?cnpj\*? do titular",
     "reply": "{titular_cnpj}", "requires": ["titular_cnpj"], "fallback_adaptive": True,
     "notes": "📊 1 tela / 5 sessões. A porta do galho condomínio."},
    {"step": "aviso_areas_comuns", "anchor": r"exclusivamente destinados [àa]s [áa]reas comuns",
     "reply": "", "noop": True,
     "notes": "📊 1 tela / 5 ses. 🔴 REGRA DE COBERTURA: o serviço NÃO cobre unidade "
              "individual. Vai a `regras_para_o_cliente` — é o que o cliente precisa "
              "ouvir ANTES, para não receber uma recusa no local."},
    {"step": "numero_condominio", "anchor": r"me confirme o n[úu]mero do condom[íi]nio",
     "reply": "{endereco_numero}", "fallback_adaptive": True, "notes": "📊 1 tela / 5 sessões."},

    # ---- coleta e desfecho ------------------------------------------------
    {"step": "referencias_do_local", "anchor": r"informe \*?refer[êe]ncias do local",
     "reply": "{ponto_referencia}", "fallback_adaptive": True, "notes": "📊 1 tela / 5 sessões."},
    {"step": "senha_do_telefone", "anchor": r"o telefone registrado nesse atendimento",
     "reply": "", "noop": True,
     "notes": "📊 3 telas / 10 sessões. Traz a SENHA da visita (4 últimos dígitos). Quem "
              "a colhe é `capture_anchors.password`; o passo existe para o motor ficar "
              "calado enquanto a captura acontece."},
    {"step": "link_por_sms", "anchor": r"receber[áa] um link por \*?sms\*? para acompanhar",
     "reply": "", "noop": True,
     "notes": "📊 1 tela / 10 sessões. ⚠️ SÓ no residencial: medido, no corredor de AUTO "
              "esta âncora ROUBA 7 telas que `desfecho_protocolo_alfa` já responde."},
    {"step": "link_acompanha", "anchor": r"acompanhar a chegada do nosso parceiro pelo link",
     "reply": "", "noop": True, "notes": "📊 2 telas / 7 sessões."},
]

_ALLIANZ_AMBOS = [
    # 🔴 A tela do ACOMPANHAR/ALTERAR — 📊 auto 3 ses · residencial 10 ses.
    #    Não é acionamento novo: é pós-serviço. A resposta vem do caso, porque
    #    "2 - Abrir novo" e "1 - Ver detalhes" são trabalhos diferentes.
    {"step": "solicitacao_ja_feita",
     "anchor": r"identifiquei que temos uma solicita[çc][ãa]o de servi[çc]o feita",
     "reply": "{solicitacao_existente_opcao}", "requires": ["solicitacao_existente_opcao"],
     "fallback_adaptive": True,
     "notes": "📊 auto 3 ses · resid 10 ses. 1-Ver detalhes 2-Abrir novo. 🔴 Vem do caso: "
              "quem ligou por um problema NOVO não quer ver o chamado antigo, e "
              "vice-versa."},
    {"step": "uf_do_local", "anchor": r"informe a \*?uf\*? \(sigla do estado\) do local",
     "reply": "{local_uf}", "fallback_adaptive": True, "notes": "📊 1 tela / 4 sessões."},
    {"step": "profissional_a_caminho", "anchor": r"o profissional chegar[áa] o mais r[áa]pido poss[íi]vel",
     "reply": "", "noop": True, "notes": "📊 1 tela / 2 sessões."},
]

ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = (
    list(ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"])
    + [dict(p) for p in _ALLIANZ_RESID_TRONCO + _ALLIANZ_AMBOS]
)
ALLIANZ_AUTO_WHATSAPP_V1["ura_steps"] = (
    list(ALLIANZ_AUTO_WHATSAPP_V1["ura_steps"]) + [dict(p) for p in _ALLIANZ_AMBOS]
)


# ==========================================================================
# BLOCO 4 — OS SERVIÇOS QUE A URA OFERECE E O PRODUTO RECUSAVA
# ==========================================================================
#
# 🔴 A regra que autoriza cada um destes, e ela é a mesma do `desentupimento`
#    da Allianz: *"um mesmo trabalho existir num corredor e não no outro não é
#    escopo: é esquecimento."*
#
# Nenhum entra por rótulo avistado. Cada um tem, medido no acervo:
#   · o rótulo do menu, com a grafia exata
#   · o fluxo depois dele, tela a tela
#   · e — nos quatro que o Founder liberou — **uma sessão completa até o
#     protocolo**
#
# ⚠️ E a porta continua fechada para quem não tem isso: `Motorista da vez`,
#    `Martelinho de ouro`, `Assistência Mercosul`, `Kit instalação`,
#    `Reparo em telha` e `Limpeza de calhas` têm rótulo capturado e **ZERO**
#    sessões que entraram. Declarar tecla sem fluxo é o defeito que
#    `_ativar_vidros` proíbe por escrito. Eles ficam em PENDENCIAS.


def _ativar_subservico(playbook, nome, *, menu_value, required_slots,
                       label, outcome=OUTCOME_ABRE, referral=None,
                       espera_no_local=False):
    """Liga um subserviço NUMA seguradora — nunca em `_AUTO_SUBSERVICES`.

    🔴 `_auto_playbook` copia `_AUTO_SUBSERVICES` para as ONZE seguradoras de
    auto. Acrescentar ali ligaria `táxi` na mapfre, na zurich e na azul sem uma
    única tela observada — que é exatamente o erro que este produto já nomeou.

    Chamar esta função é uma AFIRMAÇÃO DE EVIDÊNCIA: existe menu capturado, ele
    diz exatamente `menu_value`, e existe fluxo medido depois dele.
    """
    playbook.setdefault("subservices", {})[nome] = {
        "required_slots": list(required_slots),
        **({"outcome": outcome} if outcome != OUTCOME_ABRE else {}),
        **({"referral": dict(referral)} if referral else {}),
    }
    if menu_value is not None:
        playbook.setdefault("subservice_menu_map", {})[nome] = menu_value
    playbook.setdefault("subservice_labels", {})[nome] = label
    if espera_no_local and nome not in _SUBSERVICOS_COM_ALGUEM_NO_LOCAL:
        _SUBSERVICOS_COM_ALGUEM_NO_LOCAL.append(nome)


# --------------------------------------------------------------------------
# PORTO · auto · TÁXI
# --------------------------------------------------------------------------
# 📊 rótulo em **13 de 13** menus · 37 msgs · 13 sessões · sub-fluxo completo em
#    2 sessões (c5cafa8b, c470d13d), a última chegando a
#    "Posso confirmar sua solicitação? Sim / Não, alterar endereço / Sair".
#
# ⚠️ E a ambiguidade que fica registrada: o corpus mostra os DOIS caminhos —
#    táxi oferecido DEPOIS do guincho ("Você também precisa solicitar um
#    táxi?") e táxi aberto SOZINHO. Declarar como subserviço resolve o segundo;
#    o primeiro precisa de um conceito de "serviço encadeado" que não existe.
_ativar_subservico(
    PORTO_AUTO_WHATSAPP_V1, "taxi",
    menu_value="Táxi",
    required_slots=_AUTO_SLOTS_COMMON + ["local_destino", "taxi_passageiros"],
    label="táxi (meio de transporte)",
    espera_no_local=True,
)
PORTO_AUTO_WHATSAPP_V1["ura_steps"] = list(PORTO_AUTO_WHATSAPP_V1["ura_steps"]) + [
    {"step": "taxi_passageiros",
     "anchor": r"eu vou chamar um t[áa]xi para voc[êe]\. s[ãa]o quantos passageiros",
     "reply": "1 a 4", "fallback_adaptive": True, "only_subservices": ["taxi"],
     "notes": "📊 1/1."},
    {"step": "taxi_cadeirinha",
     "anchor": r"caso o t[áa]xi tenha que transportar alguma crian[çc]a",
     "reply": "", "noop": True, "only_subservices": ["taxi"],
     "notes": "📊 1/1. 🔴 REGRA AO CLIENTE: criança de até 7 anos exige que VOCÊ "
              "disponibilize bebê conforto/cadeirinha."},
    {"step": "taxi_mesmo_endereco",
     "anchor": (r"o t[áa]xi deve ir para o mesmo endere[çc]o|"
                r"o endere[çc]o [ée] o mesmo de destino do guincho"),
     "reply": "Sim", "only_subservices": ["taxi"],
     "constante_justificada": (
         "📊 2 sessões. O táxi da porto só é oferecido no encadeamento do guincho, e "
         "nas duas o destino é o mesmo. Se o caso trouxer `local_destino` diferente, "
         "é outro trabalho — e o corredor não tem como saber disso nesta tela."),
     "notes": "📊 2/2."},
    {"step": "taxi_destino_sabe", "anchor": r"voc[êe] j[áa] sabe (?:a)?onde o t[áa]xi dever[áa] te levar",
     "reply": "Sim", "only_subservices": ["taxi"],
     "constante_justificada": "📊 1 sessão. O corredor só abre táxi com `local_destino` no caso.",
     "notes": "📊 1/1."},
    {"step": "taxi_sem_paradas", "anchor": r"o t[áa]xi ir[áa] at[ée] o endere[çc]o de destino",
     "reply": "", "noop": True, "only_subservices": ["taxi"],
     "notes": "📊 1/1. 🔴 REGRA AO CLIENTE: o táxi vai SEM FAZER PARADAS no caminho."},
]

# --------------------------------------------------------------------------
# PORTO · auto · TÉCNICO  (o "socorro mecânico" da porto)
# --------------------------------------------------------------------------
# 📊 rótulo em 10 de 13 menus · 27 msgs · 12 sessões · **2 sessões inteiras até
#    o protocolo** (b1ff65f2 com 42 telas, e5318468 com 34).
#
# 🔴 É a maior evidência não-codificada da porto. E o desfecho é OUTRO: o
#    técnico é AGENDADO por janela de meia hora ("Entre 14h00 e 14h30"),
#    enquanto guincho/bateria/pneu/chaveiro prometem "hoje, em até 60 minutos".
#    Sem `local_destino`: não há para onde levar.
_ativar_subservico(
    PORTO_AUTO_WHATSAPP_V1, "tecnico",
    menu_value="Técnico",
    required_slots=_AUTO_SLOTS_COMMON + ["veiculo_cor"],
    label="técnico (reparo no local)",
    espera_no_local=True,
)
PORTO_AUTO_WHATSAPP_V1["ura_steps"] = list(PORTO_AUTO_WHATSAPP_V1["ura_steps"]) + [
    {"step": "tecnico_pode_virar_guincho",
     "anchor": r"caso o t[ée]cnico avalie que o ve[íi]culo precisa",
     "reply": "", "noop": True, "only_subservices": ["tecnico"],
     "notes": "📊 1/1. 🔴 REGRA AO CLIENTE: a própria URA avisa que o caso pode "
              "virar guincho — e aí é OUTRO acionamento."},
]

# --------------------------------------------------------------------------
# PORTO · auto · BATERIA NOVA
# --------------------------------------------------------------------------
# 📊 submenu em 5 sessões · 1 sessão completa até o resumo (f4838bb3).
#
# 🔴 NÃO é variação de `bateria`: é outro trabalho, com outro desfecho e com
#    DINHEIRO DO CLIENTE. "Para solicitar a nova bateria, precisamos agendar a
#    *visita técnica de um prestador da Porto*" — agendado, e o valor da
#    bateria é do segurado.
#    Hoje `bateria` responde "Recarga de bateria" fixo: quem precisa de bateria
#    nova recebe recarga.
_ativar_subservico(
    PORTO_AUTO_WHATSAPP_V1, "bateria_nova",
    menu_value="Bateria nova",
    required_slots=_AUTO_SLOTS_COMMON + ["data_agendamento"],
    label="bateria nova (visita técnica agendada)",
    espera_no_local=True,
)
PORTO_AUTO_WHATSAPP_V1["ura_steps"] = list(PORTO_AUTO_WHATSAPP_V1["ura_steps"]) + [
    {"step": "bateria_nova_visita",
     "anchor": r"precisamos agendar a\s*[\s\S]{0,3}visita t[ée]cnica de um prestador",
     "reply": "", "noop": True, "only_subservices": ["bateria_nova"],
     "notes": "📊 1/1."},
    {"step": "bateria_nova_preco",
     "anchor": r"prestador fornecer[áa] as informa[çc][õo]es sobre a marca, descarte",
     "reply": "", "noop": True, "only_subservices": ["bateria_nova"],
     "notes": "📊 1/1. 🔴 A tela traz PREÇO ao cliente. Ela é `noop` porque não pede "
              "resposta — mas o texto vai a `regras_para_o_cliente`, e o segurado "
              "precisa ouvir isso ANTES."},
]

# --------------------------------------------------------------------------
# PORTO · residencial · CHAVEIRO  (🔴 o mais gritante dos quatro)
# --------------------------------------------------------------------------
# 📊 rótulo em 4 de 4 menus · 10 msgs · 6 sessões · **1 sessão COMPLETA até o
#    protocolo** (565cb39a, 37 telas), com DOIS submenus mapeados e regra de
#    cobertura própria.
#
# 🔴 Existe uma rota-ouro inteira no acervo, e `subservice_supported()` devolvia
#    **False**. É o `desentupimento` da Allianz outra vez.
#
# ⚠️ E os rótulos divergem entre as duas variantes do menu: "Chaveiro
#    residencial" (A) x "Chaveiro" (B). Por isso o mapa recebe o rótulo da
#    variante VIVA e o corredor tem `unknown_step_policy` para a outra.
PORTO_RESIDENCIAL_WHATSAPP_V1.setdefault("subservices", {})["chaveiro"] = {
    "required_slots": _resid_slots("chaveiro"),
}
PORTO_RESIDENCIAL_WHATSAPP_V1.setdefault("subservice_labels", {})["chaveiro"] = (
    "assistencia de chaveiro")
PORTO_RESIDENCIAL_WHATSAPP_V1.setdefault("subservices", {})["desentupimento"] = {
    "required_slots": _resid_slots("desentupimento"),
}
PORTO_RESIDENCIAL_WHATSAPP_V1.setdefault("subservice_labels", {})["desentupimento"] = (
    "desentupimento")

PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = list(
    PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"]) + [
    # ---- o menu de serviço residencial (as DUAS variantes) ---------------
    # 🔴 SETE dos nove rótulos MUDAM entre as variantes A e B (singular/plural,
    #    "Chaveiro residencial" x "Chaveiro", "Chuveiro" x "Técnico para
    #    chuveiro", "Limpeza de calhas" x "Limpeza de calha"). Só "Encanador
    #    (Hidráulica)" e "Eletricista" são idênticos nas duas.
    #    Por isso a resposta vem do CASO e não de um rótulo fixo por subserviço:
    #    um mapa com um rótulo só erra em uma das duas variantes para 7 dos 9.
    {"step": "menu_servico_resid",
     "anchor": (r"o que voc[êe] precisa\?[\s\S]{0,300}"
                r"(?:encanador \(hidr[áa]ulica\)|eletrodom[ée]stic)"),
     "reply": "{servico_texto}", "fallback_adaptive": True,
     "notes": "📊 4 msgs / 4 sessões, DUAS variantes com listas DIFERENTES."},
    # ---- chaveiro: os dois submenus da rota-ouro -------------------------
    {"step": "chaveiro_sem_instalacao", "anchor": r"n[ãa]o realizamos instala[çc][ãa]o de fechaduras",
     "reply": "", "noop": True, "only_subservices": ["chaveiro"],
     "notes": "📊 1/1. 🔴 EXCLUSÃO DE COBERTURA: a Porto faz REPARO e ABERTURA, "
              "não instalação."},
    {"step": "chaveiro_submenu", "anchor": r"voc[êe] precisa do chaveiro para o qu[êe]",
     "reply": "{chaveiro_alvo_opcao}", "requires": ["chaveiro_alvo_opcao"],
     "fallback_adaptive": True, "only_subservices": ["chaveiro"],
     "notes": "📊 1/1. 1-Porta ou janela 2-Portão 3-Fechadura 4-Não encontrei 5-Voltar."},
    {"step": "chaveiro_tipo_fechadura", "anchor": r"qual tipo de fechadura precisa de reparo",
     "reply": "{fechadura_tipo_opcao}", "requires": ["fechadura_tipo_opcao"],
     "fallback_adaptive": True, "only_subservices": ["chaveiro"],
     "notes": "📊 1/1. 1-Comum 2-Tetra 3-Eletrônica/Digital 4-Não encontrei 5-Voltar."},
    # ---- encanador: o submenu que contém o DESENTUPIMENTO ----------------
    # 📊 "*1* - Desentupimento *2* - Vazamento *3* - Reparo *4* - Assistência
    #    para Chuveiro *5* - Instalações *6* - Voltar"
    # 🔴 `desentupimento` não tem rótulo no menu principal: entra por
    #    "Encanador (Hidráulica)" e depois pela tecla 1. É uma rota de DUAS
    #    teclas, e as duas estão medidas.
    {"step": "encanador_submenu",
     "anchor": r"para qual tipo de servi[çc]o\?[\s\S]{0,120}desentupimento",
     "reply": "{encanador_tipo_opcao}", "requires": ["encanador_tipo_opcao"],
     "fallback_adaptive": True, "only_subservices": ["encanador", "desentupimento"],
     "notes": "📊 1/1."},
    {"step": "encanador_instalacao", "anchor": r"o que precisa de instala[çc][ãa]o\?",
     "reply": "{encanador_instalacao_opcao}", "requires": ["encanador_instalacao_opcao"],
     "fallback_adaptive": True, "only_subservices": ["encanador"],
     "notes": "📊 1/1. 1-Filtro/Purificador 2-Torneira 3-Ducha higiênica."},
    {"step": "encanador_recados",
     "anchor": r"n[ãa]o faz reparo de equipamentos de pressuriza[çc][ãa]o",
     "reply": "", "noop": True, "only_subservices": ["encanador", "desentupimento"],
     "notes": "📊 1/1. 🔴 DUAS EXCLUSÕES numa frase: não faz pressurização, e não faz "
              "o reparo se precisar interromper a água de TERCEIROS."},
]


# ==========================================================================
# 🔴 SOCORRO MECÂNICO — 2º EM DEMANDA MEDIDA, E O PRODUTO RECUSAVA
# ==========================================================================
#
# 📊 `DEMANDA_MEDIDA`: 7 escolhido / 70 no cardápio. E `subservice_supported`
#    devolvia **False** em todas as seguradoras: `_AUTO_SUBSERVICES` tem
#    guincho/bateria/pneu/chaveiro e mais nada.
#
# 🔴 E O MOTIVO DE ELE NÃO EXISTIR NO CÓDIGO É QUE **ELE NÃO É UM BOTÃO DO
#    MENU.** O menu real, transcrito inteiro:
#
#      "Pode me dizer o que aconteceu? Para isso *selecione* uma das opções.
#       Pane ou Defeito · Recarga de bateria · Houve uma colisão ·
#       Pneu Furado · Problema com a chave · Falta de combustível · Voltar"
#
#    Não há "Socorro mecânico". **"Socorro Mecânico" é o nome que a URA dá ao
#    DESFECHO** — o que ela escreve em `*Resumo da solicitação* *Serviço:*`
#    quando decide mandar um mecânico ao local em vez de um reboque.
#
# 📊 O fluxo, medido turno a turno na sessão 71caf82f (hdi-auto, 01/06/2026,
#    protocolo 9662631, 100% bot, ponta a ponta):
#
#      identificacao_dado -> continuar_com_placa -> informar_nome -> perfil
#      -> pessoa_no_local -> nome_pessoa_local -> telefone_local
#      -> telefone_confirma -> cor -> rodovia
#      -> o_que_aconteceu = "Pane ou Defeito"
#      -> pane_detalhe    = "Problemas elétricos"     🔴 e o corredor respondia
#                                                        "Problemas no motor" FIXO
#      -> descreva_situacao -> aviso_recarga_bateria
#      -> endereço -> situacao_risco -> ocupantes
#      -> quando_agora = "Agora"                      <- PONTO DE NÃO-RETORNO
#      -> *Serviço:* Socorro Mecânico  *Assistência:* 9662631
#
#    📊 Mais 4 sessões na yelum-auto (927d8cea, 8ac461dc, 935c4076, 86769bd5),
#       protocolos 9755758 · 9874835 · 9904302 · 9423652, mesmo caminho.
#
# 🔴 A TECLA É A MESMA DO GUINCHO ("Pane ou Defeito"). Quem separa os dois é a
#    tela SEGUINTE — `pane_detalhe` —, e é por isso que a constante
#    "Problemas no motor" que existia ali era grave: ela decidia a pane do
#    segurado, e a pane é o que a URA usa para escolher entre reboque e
#    mecânico no local.
#
# ⚠️ SEM `local_destino`: não há para onde levar. Um mecânico vai ATÉ o veículo.
#
# 🔴 E ele é ligado APENAS onde o fluxo foi observado. `_auto_playbook` copia
#    `_AUTO_SUBSERVICES` para as ONZE seguradoras — acrescentar lá ligaria
#    socorro mecânico na porto, na azul e na mapfre sem uma tela vista.
for _pb_sm in (HDI_AUTO_WHATSAPP_V1, YELUM_AUTO_WHATSAPP_V1, ZURICH_AUTO_WHATSAPP_V1):
    _ativar_subservico(
        _pb_sm, "socorro_mecanico",
        menu_value=(_pb_sm.get("subservice_menu_map") or {}).get("guincho"),
        required_slots=[x for x in _AUTO_SLOTS_COMMON if x != "local_destino"],
        label="socorro mecânico (reparo no local)",
        espera_no_local=True,
    )

# 🔴 E O SEGURADO NÃO DIZ "socorro mecânico" — ele diz o que está acontecendo.
_SUBSERVICE_ALIASES.update({
    "socorro mecanico": "socorro_mecanico", "socorro_mecanico": "socorro_mecanico",
    "mecanico": "socorro_mecanico", "pane": "socorro_mecanico",
    "pane eletrica": "socorro_mecanico", "pane mecanica": "socorro_mecanico",
    "carro nao liga": "socorro_mecanico", "nao pega": "socorro_mecanico",
    "motor falhando": "socorro_mecanico", "defeito": "socorro_mecanico",
})

# ==========================================================================
# AR CONDICIONADO — allianz residencial
# ==========================================================================
# 📊 O menu `menu_outros_servicos_residencia` (2 telas / 21 sessões) nomeia o
#    trabalho, e a tela do galho ("*1 -* Conserto do ar condicionado *2 -*
#    Limpeza") tem passo desde o conserto do OITAVO defeito.
#
# ⚠️ IDENTIFICADA, NÃO ESTABELECIDA: nenhuma sessão chegou ao protocolo por
#    aqui. O subserviço é declarado com `pause_and_handoff` herdado do corredor
#    — a tecla é comprovada, o resto pausa. É melhor que recusar um trabalho
#    que a seguradora faz.
ALLIANZ_RESIDENCIAL_WHATSAPP_V1["subservices"]["ar_condicionado"] = {
    "tipo_servico_opcao": "2",
    "eletrodomestico_categoria_opcao": "2",
    "required_slots": [
        "titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao",
        "aparelho_marca", "aparelho_modelo", "periodo_preferido",
        "idade_aparelho_opcao", "qual_seguro_opcao",
    ],
}
ALLIANZ_RESIDENCIAL_WHATSAPP_V1.setdefault("subservice_labels", {})["ar_condicionado"] = (
    "conserto de ar condicionado")
_SUBSERVICE_ALIASES.update({
    "ar condicionado": "ar_condicionado", "ar-condicionado": "ar_condicionado",
    "arcondicionado": "ar_condicionado", "split": "ar_condicionado",
    "ar nao gela": "ar_condicionado",
})

_PLAYBOOKS_AUTO_COM_PNEU = [
    pb for pb in (ALLIANZ_AUTO_WHATSAPP_V1, ALFA_AUTO_WHATSAPP_V1,
                  AZUL_AUTO_WHATSAPP_V1, PORTO_AUTO_WHATSAPP_V1,
                  YELUM_AUTO_WHATSAPP_V1, HDI_AUTO_WHATSAPP_V1,
                  ZURICH_AUTO_WHATSAPP_V1, BRADESCO_AUTO_WHATSAPP_V1,
                  MAPFRE_AUTO_WHATSAPP_V1, TOKIO_AUTO_WHATSAPP_V1)
    if pb is not None
]


# ==========================================================================
# 🔴 OS SLOTS QUE DECIDEM COBERTURA — E QUE NINGUÉM PODE ADIVINHAR
# ==========================================================================
#
# 📊 Achados pelo conferidor de respostas: eram respondidos pelo cérebro
#    (`fallback_adaptive`), e o cérebro está lendo a tela — não sabendo o fato.
#
# A regra que separa estes dos derivados:
#
# ```
# DERIVA   o que o segurado JA DISSE   ("furei dois pneus" -> 2)
# COLETA   o que so ele sabe E que decide COBERTURA
# ```
#
# 🔴 Um estepe furado não está no relato de ninguém. E responder "tenho estepe"
#    por preguiça manda um BORRACHEIRO para um carro que precisa de REBOQUE: o
#    prestador chega, olha, e vai embora — e o acionamento conta como usado.
#
# 🔴 Pior é `local_seguro`. Responder "sim" no escuro **rebaixa a prioridade de
#    quem está parado num lugar perigoso**. É a mesma regra já escrita em
#    `rb_InformacoesLocal` do flow nativo, aplicada aos passos.
_SLOTS_DE_COBERTURA_AUTO = [
    "estepe_situacao",          # 📊 "Em condições / Sem condições / Não" -- e
                                #    NENHUMA das três é "Sim". Duas levam a guincho.
    "ferramentas_no_veiculo",   # 📊 "Possui chave de roda e macaco em boas condições?"
    "equipamentos_troca_opcao",  # 📊 alfa: chave de roda, macaco E step, juntos
    "local_seguro",             # 🔴 decide PRIORIDADE, não cobertura
]
for _sv_pneu in ("pneu",):
    for _pb_cob in _PLAYBOOKS_AUTO_COM_PNEU:
        sub = (_pb_cob.get("subservices") or {}).get(_sv_pneu)
        if sub is not None:
            sub["required_slots"] = list(sub["required_slots"]) + [
                x for x in _SLOTS_DE_COBERTURA_AUTO
                if x not in sub["required_slots"]]

# `local_seguro` vale para TODO subserviço de auto: o segurado pode estar na
# rua em qualquer um deles. 📊 A URA pergunta em guincho, bateria e pneu.
for _pb_cob in _PLAYBOOKS_AUTO_COM_PNEU:
    for _nome_sv, sub in (_pb_cob.get("subservices") or {}).items():
        if _nome_sv == "vidros":
            continue  # 📊 vidro é agendado; ninguém espera na rua
        if "local_seguro" not in sub.get("required_slots", []):
            sub["required_slots"] = list(sub.get("required_slots") or []) + ["local_seguro"]

# 🔴 E o RESIDENCIAL tem o seu: casa ou condomínio decide se a URA vai pedir os
#    dois horários de entrada do prestador. 📊 Sem eles, o prestador não entra
#    no prédio — e a corretora sabe o tipo do imóvel, o segurado não precisa
#    ser perguntado duas vezes.
for _pb_resid in (HDI_RESIDENCIAL_WHATSAPP_V1, YELUM_RESIDENCIAL_WHATSAPP_V1):
    for sub in (_pb_resid.get("subservices") or {}).values():
        if "tipo_imovel" not in (sub.get("required_slots") or []):
            sub["required_slots"] = list(sub.get("required_slots") or []) + ["tipo_imovel"]


# ==========================================================================
# BLOCO 4 · parte 3 — o menu `Outros serviços` da allianz, e o técnico da azul
# ==========================================================================
#
# 📊 O menu que nomeia estes trabalhos tem **2 telas / 21 sessões**:
#   "*1 -* Dedetização *2 -* Limpeza do Imóvel *3 -* Limpeza de Caixa d'Água
#    *4 -* Substituição de Telhas *5 -* Cobertura Provisória de Telhado
#    *6 -* Consulta Veterinária *7 -* Outros *8 -* Voltar"
#
# 🔴 Dos oito, DOIS têm fluxo medido até o PROTOCOLO. Os outros ficam em
#    PENDENCIAS com o que destrava — e é essa a diferença entre "declarar por
#    rótulo avistado" e "declarar por conversa clara".
#
#   📊 limpeza_caixa_dagua   4 sessões · 1 chega ao protocolo   -> 🟢 LIGA
#   📊 consulta_veterinaria  1 sessão  · 1 chega ao protocolo   -> 🟢 LIGA
#   📊 telhado               1 sessão  · 0 chegam               -> ⏸️ PENDENCIAS
#   📊 pet assistance        1 sessão  · 1 chega                -> ⏸️ outra linha de produto
#   📊 dedetização / limpeza do imóvel                          -> ⏸️ sem sessão
ALLIANZ_RESIDENCIAL_WHATSAPP_V1["subservices"]["limpeza_caixa_dagua"] = {
    "tipo_servico_opcao": "2",
    "outro_servico_opcao": "3",
    "required_slots": [
        "titular_cpf", "endereco_numero", "telefone_contato", "problema_descricao",
        "periodo_preferido", "qual_seguro_opcao", "caixas_dagua_quantidade_opcao",
        # 🔴 SO O CLIENTE SABE, e decide o EQUIPAMENTO: ate 2.500 litros x
        #    acima. Nenhum relato de vazamento diz o volume da caixa d agua.
        "caixa_litros_opcao",
    ],
}
ALLIANZ_RESIDENCIAL_WHATSAPP_V1["subservices"]["consulta_veterinaria"] = {
    "tipo_servico_opcao": "2",
    "outro_servico_opcao": "6",
    "required_slots": [
        "titular_cpf", "telefone_contato", "problema_descricao", "qual_seguro_opcao",
    ],
}
ALLIANZ_RESIDENCIAL_WHATSAPP_V1.setdefault("subservice_labels", {}).update({
    "limpeza_caixa_dagua": "limpeza de caixa d'agua",
    "consulta_veterinaria": "consulta veterinaria",
})
_SUBSERVICE_ALIASES.update({
    "limpeza de caixa d agua": "limpeza_caixa_dagua",
    "limpeza de caixa dagua": "limpeza_caixa_dagua",
    "caixa d agua": "limpeza_caixa_dagua", "caixa dagua": "limpeza_caixa_dagua",
    "limpar caixa": "limpeza_caixa_dagua",
    "consulta veterinaria": "consulta_veterinaria",
    "veterinario": "consulta_veterinaria", "veterinaria": "consulta_veterinaria",
    "pet": "consulta_veterinaria",
})

ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = list(
    ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"]) + [
    {"step": "caixa_dagua_agendar",
     "anchor": r"limpeza de caixa d.?[áa]gua\*? dever[áa] ser agendado",
     "reply": "1", "only_subservices": ["limpeza_caixa_dagua"],
     "constante_justificada": (
         "📊 2 sessões. 1-Continuar 2-Voltar. Quem pediu a limpeza quer continuar — "
         "é navegação, não escolha de conteúdo."),
     "notes": "📊 2 telas / 2 sessões."},
    {"step": "caixa_dagua_quantas",
     "anchor": r"quantas caixas d.?[áa]gua precisam do servi[çc]o",
     "reply": "{caixas_dagua_quantidade_opcao}",
     "requires": ["caixas_dagua_quantidade_opcao"], "fallback_adaptive": True,
     "only_subservices": ["limpeza_caixa_dagua"],
     "notes": "📊 2 telas / 2 sessões. 1-uma unidade 2-duas unidades. "
              "🔴 Vem do caso: o número de caixas muda o preço e o tempo do serviço."},
]

# --------------------------------------------------------------------------
# AZUL · auto · TÉCNICO — ⚠️ IDENTIFICADA, NÃO ESTABELECIDA
# --------------------------------------------------------------------------
# 📊 1 sessão (d70ced75), 33 telas, e **não chega ao protocolo**. Os quatro
#    passos do galho já estão escritos (`tecnico_agendamento`, `tecnico_data`,
#    `tecnico_periodo`, `tecnico_horario`) e casavam no vazio, porque
#    `subservice_supported` devolvia False.
#
# 🔴 E o desfecho é OUTRO: AGENDADO por faixa de 30 minutos, não "hoje em até
#    60 minutos". Se um dia o pneu da azul entrar por aqui — é o candidato
#    medido — a `expectativa_do_desfecho` muda junto.
_ativar_subservico(
    AZUL_AUTO_WHATSAPP_V1, "tecnico",
    menu_value="Técnico",
    required_slots=_AUTO_SLOTS_COMMON + ["data_agendamento"],
    label="técnico (reparo no local, AGENDADO)",
    espera_no_local=True,
)


# ==========================================================================
# PORTO · residencial — O GALHO (SPEC-084 BLOCO 2, 22/08/2026)
# ==========================================================================
#
# 📊 3 rotas em `NAO_RESPONDE`, 28 órfãs funcionais, determinismo 50%. O BLOCO 1
#    escreveu o TRONCO da porto e parou — e o tronco sozinho não fecha um
#    acionamento: ele identifica o cliente e emudece na primeira pergunta do
#    trabalho.
_PORTO_RESID_GALHO = [
    # ---- o menu de atendimento: TRES listas, um rotulo estavel -----------
    # 🔴 📊 Em duas variantes o rótulo é "Novo serviço"; na terceira é
    #    "SOLICITAR novo serviço", e essa é numerada (aceita "1"). A opção 1 é a
    #    mesma nas três.
    # ⚠️ E a opção 3 é CANCELAR SERVIÇO: tecla errada aqui cancela um chamado
    #    que já existe.
    {"step": "menu_atendimento_resid", "anchor": r"de que atendimento voc[êe] precisa",
     "reply": "Novo serviço", "fallback_adaptive": True,
     "constante_justificada": (
         "📊 5 msgs / 5 sessões, TRÊS listas. O corredor existe para ABRIR — "
         "acompanhar, cancelar e consultar saldo são outros trabalhos. "
         "🔴 E 'Cancelar serviço' está na mesma lista: com `fallback_adaptive`, "
         "se o rótulo não bater, o cérebro lê a tela em vez de arriscar."),
     "notes": "📊 5 msgs / 5 sessões."},

    # ---- o endereco -------------------------------------------------------
    # ⚠️ 📊 6 telas, e UMA mostra DOIS endereços quase idênticos
    #    (`SL 330 CAMP A` × `Sl 330 Camp A`). "Endereço 1" fixo funciona em 5 de
    #    6 e escolhe às cegas na sexta — por isso `fallback_adaptive`.
    {"step": "escolher_endereco_resid", "anchor": r"o servi[çc]o [ée] para qual endere[çc]o",
     "reply": "Endereço 1", "fallback_adaptive": True,
     "constante_justificada": (
         "📊 6 telas / 6 sessões. 'Endereço 1' é o da apólice. Em 1 das 6 há dois "
         "endereços quase idênticos — ali o adaptativo assume, porque escolher às "
         "cegas manda o prestador para a casa errada."),
     "notes": "📊 6 msgs / 6 sessões."},
    {"step": "ponto_referencia_resid",
     "anchor": r"pode me informar algum\s*[\s\S]{0,3}ponto de refer[êe]ncia",
     "reply": "{ponto_referencia}", "fallback_adaptive": True,
     "notes": "📊 7 msgs / 7 sessões."},

    # ---- o agendamento ----------------------------------------------------
    {"step": "seguir_agendamento", "anchor": r"posso continuar (?:o|com o) agendamento",
     "reply": "Sim",
     "constante_justificada": (
         "📊 5 msgs / 4 sessões. 1-Sim 2-Não, e o corredor está aqui justamente "
         "para continuar. Parar seria abandonar o acionamento no meio."),
     "notes": "📊 5 msgs / 4 sessões."},
    {"step": "menu_quando_resid", "anchor": r"para quando voc[êe] precisa que esse servi[çc]o",
     "reply": "Tenho urgência",
     "constante_justificada": (
         "📊 4 msgs / 4 sessões. O corredor só roda para acionamento aberto agora. "
         "⚠️ E a URA avisa na MESMA tela que 'a solicitação será confirmada somente "
         "após a finalização' — o texto vai ao cliente, não muda a tecla."),
     "notes": "📊 4 msgs / 4 sessões."},
    {"step": "data_agendamento_resid",
     "anchor": r"informe para quando voc[êe] (?:quer|quiser) agendar o servi[çc]o",
     "reply": "{data_agendamento}", "fallback_adaptive": True,
     "notes": "📊 resid 3/3 · auto 1/1."},
    # 🔴 DUAS listas: manhã/tarde/noite/Voltar (encanador) e
    #    manhã/tarde/noite/MADRUGADA/Voltar (chaveiro). As TRÊS primeiras teclas
    #    coincidem; a quarta não. Um mapa até 3 é seguro; acima disso não é.
    {"step": "periodo_agendamento_resid", "anchor": r"qual per[íi]odo voc[êe] prefere",
     "reply": "{periodo_agendamento_opcao}", "fallback_adaptive": True,
     "notes": "📊 resid 3/3 · auto 1/1. DUAS listas, e só as 3 primeiras teclas "
              "coincidem entre elas."},
    {"step": "horario_agendamento_resid",
     "anchor": r"^e qual hor[áa]rio\?|os hor[áa]rios mais pr[óo]ximos que eu tenho aqui",
     "reply": "{horario_opcao}", "fallback_adaptive": True,
     "notes": "📊 resid 5/4 · auto 1/1."},
    {"step": "novo_agendamento", "anchor": r"deseja realizar o agendamento de um novo servi[çc]o",
     "reply": "Não",
     "constante_justificada": (
         "📊 3 msgs / 3 sessões. Um acionamento por vez: o corredor abre O QUE a "
         "corretora pediu. Um segundo serviço é outro caso."),
     "notes": "📊 3/3."},

    # ---- quem recebe o prestador ------------------------------------------
    # 🔴 A âncora do `no_local` da porto exigia "acompanhar|aguardar"; a tela
    #    residencial diz "RECEBER o prestador", e por isso ficava órfã em 4
    #    sessões — inclusive nas duas do fluxo-ouro (0fe42179, 565cb39a).
    {"step": "no_local_resid",
     "anchor": r"[ée] voc[êe] que est(?:[áa]|ar[áa]) no local para receber",
     "reply": "Não",
     "constante_justificada": (
         "📊 4 sessões. Mesma razão do `confirma_titular`: o WhatsApp é da "
         "CORRETORA, e quem espera na residência é o segurado. 'Sim' colocaria a "
         "corretora como responsável no local."),
     "notes": "📊 4 msgs / 4 sessões — a tela obrigatória do fluxo-ouro."},
    {"step": "descrever_necessidade",
     "anchor": r"(?:me )?explique em poucas palavras o que voc[êe] precisa",
     "reply": "{problema_descricao}", "requires": ["problema_descricao"],
     "notes": "📊 4 msgs / 3 sessões."},
    {"step": "vamos_seguir_solicitacao", "anchor": r"agora, vamos seguir com a sua solicita[çc][ãa]o",
     "reply": "", "noop": True, "notes": "📊 3/3."},
    {"step": "tudo_esta_correto", "anchor": r"tudo est[áa] correto\?", "reply": "1",
     "constante_justificada": (
         "📊 1 msg / 1 sessão. Confirmação do que NÓS enviamos — confirmar é "
         "confirmar o próprio dado."),
     "notes": "📊 1/1."},

    # ---- o pos-servico, que NAO e acionamento novo ------------------------
    # ⚠️ Estas telas são de retorno por peça, garantia e reagendamento. Não
    #    pertencem a um acionamento novo, e responder qualquer coisa nelas
    #    empurra o menu para um estado que o corredor não sabe ler.
    {"step": "menu_acompanhar_servico", "anchor": r"^certo, o que voc[êe] deseja\?",
     "reply": "", "noop": True,
     "notes": "📊 5 msgs / 4 sessões. 1-Agendar retorno por peça 2-Retorno por "
              "garantia. É PÓS-SERVIÇO."},
    {"step": "pecas_no_local",
     "anchor": r"servi[çc]o ser[áa] realizado somente se as pe[çc]as solicitadas",
     "reply": "Sim",
     "constante_justificada": (
         "📊 1 msg / 1 sessão. A URA está confirmando uma CONDIÇÃO que o segurado "
         "já cumpriu ao pedir o retorno. 🔴 O texto vai a `regras_para_o_cliente`: "
         "sem as peças no local, o prestador vem e volta."),
     "notes": "📊 1/1."},
    {"step": "servico_realizado_qual", "anchor": r"localizei que voc[êe] tem um servi[çc]o realizado",
     "reply": "", "noop": True, "notes": "📊 1/1."},
    {"step": "outros_horarios_outra_data",
     "anchor": r"para ver outros hor[áa]rios, voc[êe] precisa escolher uma data",
     "reply": "", "noop": True, "notes": "📊 1/1."},
    {"step": "reagendamento_motivo", "anchor": r"qual o motivo do reagendamento",
     "reply": "{motivo_reagendamento}", "fallback_adaptive": True, "notes": "📊 1/1."},

    # ---- venda, e nao assistencia ------------------------------------------
    {"step": "renovacao_apolice", "anchor": r"seguro est[áa] perto de expirar", "reply": "Não",
     "constante_justificada": (
         "📊 1 msg / 1 sessão. É OFERTA COMERCIAL no meio do acionamento. Aceitar "
         "em nome do segurado é decisão de compra — e ela é dele."),
     "notes": "📊 1/1."},
    {"step": "cotacao_particular", "anchor": r"voc[êe] tem interesse em realizar uma cota[çc][ãa]o",
     "reply": "2",
     "constante_justificada": (
         "📊 1 msg / 1 sessão. 1-Sim 2-Não. Mesma razão: cotação é venda, não "
         "assistência."),
     "notes": "📊 1/1."},
    {"step": "menu_assunto_resid", "anchor": r"sobre qual assunto voc[êe] quer falar", "reply": "1",
     "constante_justificada": (
         "📊 1 msg / 1 sessão. 1 = Serviços de assistência, que é a razão de o "
         "corredor existir."),
     "notes": "📊 1/1."},
]
PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = (
    list(PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"])
    + [dict(p) for p in _PORTO_RESID_GALHO]
)
# 📊 O `complemento` e o `alterar_informacao_botao` do tronco também servem o
#    galho de AUTO — e as duas listas já os têm. Aqui só o que é do residencial.


# ==========================================================================
# BLOCO 3 · PORTO auto — as folhas (guincho 72 · bateria 18 · vidros 2)
# ==========================================================================
_PORTO_AUTO_FOLHAS = [
    # ---- 🔴 O ACHADO DESTA FOLHA: a tela que É o prompt do destino --------
    # 📊 Na sessão c5cafa8b a URA **não repete** "Digite o endereço completo"
    #    para o destino. Ela manda só "Agora, vamos falar sobre o *endereço de
    #    destino*." e a mensagem seguinte já é "Localizei o endereço Rua ...".
    #    Ou seja: **essa tela É o prompt do destino**, e ela ficava órfã em 5
    #    sessões.
    #
    # ⚠️ COLISÃO DECLARADA: `endereco_livre` usa `reply_repeat: "{local_destino}"`
    #    supondo que a SEGUNDA ocorrência de "Digite o endereço completo" seria o
    #    destino. Com este passo respondendo o destino, o `reply_repeat` mandaria
    #    o destino DUAS vezes.
    # 🔴 A escolha: este passo NÃO responde — ele marca o estado e deixa o
    #    `reply_repeat` fazer o trabalho, que é o mecanismo que já está provado.
    #    Responder aqui exigiria desligar o outro, e desligar mecanismo provado
    #    para ligar mecanismo novo é troca, não ganho.
    {"step": "destino_endereco_anuncio",
     "anchor": r"vamos falar sobre o\s*[\s\S]{0,3}endere[çc]o de destino",
     "reply": "", "noop": True, "only_subservices": ["guincho", "taxi"],
     "notes": "📊 5 msgs / 5 sessões. É ANÚNCIO do destino. ⚠️ Quem responde o "
              "destino é o `reply_repeat` do `endereco_livre` — ver PENDENCIAS: "
              "os dois mecanismos não podem conviver respondendo."},

    # ---- o taxi oferecido DEPOIS do guincho -------------------------------
    {"step": "taxi_oferta", "anchor": r"voc[êe] tamb[ée]m precisa solicitar um t[áa]xi",
     "reply": "Não", "only_subservices": ["guincho"],
     "constante_justificada": (
         "📊 5 msgs / 5 sessões. 🔴 É um BENEFÍCIO COBERTO sendo recusado em nome "
         "do segurado — e é defensável porque ninguém pediu táxi: 'Sim' abre um "
         "SEGUNDO serviço no nome dele. ⚠️ Mas é decisão de PRODUTO, não de "
         "coleta, e está em PENDENCIAS. Quem quer táxi entra pela rota `taxi`, "
         "que existe desde o BLOCO 4."),
     "notes": "📊 5 msgs / 5 sessões."},

    {"step": "tecnico_agendamento_porto",
     "anchor": r"vou te ajudar com o agendamento de um t[ée]cnico",
     "reply": "", "noop": True, "notes": "📊 2 msgs / 2 sessões."},
    {"step": "autoatendimento_digital",
     "anchor": r"voc[êe] pode utilizar o\s*[\s\S]{0,3}autoatendimento digital",
     "reply": "1",
     "constante_justificada": (
         "📊 2 msgs / 2 sessões. 1-Continuar por aqui. 🔴 A alternativa é sair do "
         "WhatsApp para o app — e o corredor não consegue seguir o segurado para "
         "lá. Continuar no canal é a única opção que ele pode percorrer."),
     "notes": "📊 2/2."},
    {"step": "resumo_confira_auto",
     "anchor": r"antes de confirmar a solicita[çc][ãa]o, confira as informa[çc][õo]es",
     "reply": "", "noop": True,
     "notes": "📊 3 msgs / 3 sessões. CARDÁPIO: a escolha vem na bolha seguinte."},
    {"step": "pode_ligar_qualquer",
     "anchor": r"posso te ligar (?:no n[úu]mero abaixo|em qualquer um deles)",
     "reply": "1",
     "constante_justificada": (
         "📊 2 msgs / 2 sessões. 1-Sim, em qualquer um. O prestador ligando para "
         "MAIS números é o que aumenta a chance de achar o segurado — e a URA já "
         "só oferece números que o próprio segurado deu."),
     "notes": "📊 2/2."},
    {"step": "oficina_fechada", "anchor": r"a oficina pode estar fechada",
     "reply": "", "noop": True, "only_subservices": ["guincho"],
     "notes": "📊 2 msgs / 2 sessões. 🔴 REGRA AO CLIENTE: fora do horário "
              "comercial o guincho pode levar o veículo à base, e um SEGUNDO "
              "guincho leva à oficina no próximo dia útil."},
    {"step": "link_de_acompanhamento_url",
     "anchor": r"^https?://(?:www\.)?(?:contatoassistencia|porto)\.",
     "reply": "", "noop": True,
     "notes": "📊 3 msgs / 3 sessões. A URL sozinha numa bolha. Quem a colhe é "
              "`capture_anchors.tracking_link`; o passo existe para o motor não "
              "responder a um link."},

    # ---- endereço manual, quando o geocode falha --------------------------
    {"step": "pedir_cep_porto",
     "anchor": r"vamos tentar de outra forma\. pode, por favor, informar o cep",
     "reply": "{endereco_cep}", "fallback_adaptive": True, "notes": "📊 2/2."},
    {"step": "pedir_numero_porto",
     "anchor": (r"digite o n[úu]mero do pr[ée]dio, condom[íi]nio, casa ou km|"
                r"^qual [ée] o n[úu]mero\?\s*$"),
     "reply": "{endereco_numero}", "fallback_adaptive": True, "notes": "📊 2/2."},

    # ---- o galho dos VIDROS (demanda 2, mas o desfecho é ENCAMINHA) -------
    {"step": "vidros_retirar_veiculo",
     "anchor": r"antes da gente come[çc]ar a falar sobre o conserto",
     "reply": "2", "only_subservices": ["vidros"],
     "constante_justificada": (
         "📊 1 msg / 1 sessão. 2-Não preciso de ajuda para retirar o veículo. "
         "🔴 'Sim' abriria um GUINCHO dentro do fluxo de vidros — dois serviços "
         "num acionamento que pediu um."),
     "notes": "📊 1/1."},
    {"step": "vidros_bonus", "anchor": r"n[ãa]o ir[áa] afetar a sua classe de b[ôo]nus",
     "reply": "", "noop": True, "only_subservices": ["vidros"],
     "notes": "📊 1/1. 🔴 REGRA AO CLIENTE, e das que ele mais quer ouvir: "
              "acionar vidro NÃO mexe no bônus."},
    {"step": "vidros_link_pedido", "anchor": r"caso voc[êe] j[áa] tenha um pedido em andamento",
     "reply": "", "noop": True, "only_subservices": ["vidros"], "notes": "📊 1/1."},
]
PORTO_AUTO_WHATSAPP_V1["ura_steps"] = (
    list(PORTO_AUTO_WHATSAPP_V1["ura_steps"]) + [dict(p) for p in _PORTO_AUTO_FOLHAS]
)

# ==========================================================================
# BLOCO 3 · ALLIANZ residencial — as folhas (encanador 18 · eletricista 13)
# ==========================================================================
_ALLIANZ_RESID_FOLHAS = [
    # ---- 🔴 A TELA DO SERVIÇO JÁ ABERTO, e ela decide se o caso EXISTE ----
    # 📊 "Selecione a opção que deseja para visualizar mais informações:
    #     *1 -* *CONSERTO RESIDENCIAL*  *2 -* Abrir um novo atendimento"
    #    4 telas / 4 sessões (o rótulo do serviço muda: CONSERTO RESIDENCIAL,
    #    ENCANADOR, ...).
    # 🔴 "1" mostra o chamado ANTIGO. O corredor existe para ABRIR — e ficar
    #    preso no detalhe de um chamado velho é o caso morrer sem acionamento.
    {"step": "servico_aberto_ver_ou_abrir",
     "anchor": (r"selecione a op[çc][ãa]o que deseja para visualizar mais "
                r"informa[çc][õo]es"),
     "reply": "2",
     "constante_justificada": (
         "📊 4 telas / 4 sessões. 1-ver o chamado ANTIGO · 2-Abrir um novo "
         "atendimento. O corredor só roda quando a corretora pediu um acionamento "
         "NOVO; '1' o deixaria preso no detalhe de um chamado que já existe."),
     "notes": "📊 4 telas / 4 sessões."},

    # ---- o galho do ELETRICISTA ------------------------------------------
    {"step": "energia_da_vizinhanca",
     "anchor": r"verifique se o problema de energia [ée]/?foi em sua vizinhan[çc]a",
     "reply": "", "noop": True, "only_subservices": ["eletricista"],
     "notes": "📊 4 msgs / 4 sessões. 🔴 EXCLUSÃO DE COBERTURA: falta de energia "
              "na RUA é da concessionária, não da assistência. Vai a "
              "`regras_para_o_cliente` — o segurado precisa conferir ANTES, ou o "
              "prestador vem e não tem o que fazer."},

    # ---- o galho do ENCANADOR --------------------------------------------
    {"step": "vazamento_aparente",
     "anchor": r"o vazamento est[áa] aparente, sabe informar o local exato",
     "reply": "{vazamento_aparente_opcao}", "requires": ["vazamento_aparente_opcao"],
     "fallback_adaptive": True, "only_subservices": ["encanador", "desentupimento"],
     "notes": "📊 3 msgs / 3 sessões. 1-Sim 2-Não 3-... 🔴 Vem do caso: vazamento "
              "NÃO aparente é caça-vazamento, que costuma estar FORA da cobertura."},
    {"step": "quebra_de_alvenaria",
     "anchor": r"caso seja necess[áa]ria a quebra da alvenaria",
     "reply": "", "noop": True, "only_subservices": ["encanador", "desentupimento"],
     "notes": "📊 3 msgs / 3 sessões. 🔴 REGRA AO CLIENTE, e das que doem: o "
              "fechamento é feito no RÚSTICO — acabamento (azulejo, pintura) é "
              "por conta do segurado."},
    # 🔴 DINHEIRO — e esta tela é `noop` porque não pede resposta, mas o texto
    #    vai ao cliente ANTES do acionamento.
    {"step": "mao_de_obra_coberta_pecas_nao",
     "anchor": r"os custos de m[ãa]o de obra ser[ãa]o cobertos integralmente",
     "reply": "", "noop": True,
     "notes": "📊 3 msgs / 3 sessões. 🔴 A mão de obra é coberta; as PEÇAS são do "
              "segurado. É a regra que mais gera reclamação depois do serviço."},

    # ---- o galho da LIMPEZA DE CAIXA D'ÁGUA -------------------------------
    {"step": "caixa_dagua_limite_duas",
     "anchor": r"limitada a 0?2 \(duas\) unidades|limpeza e higieniza[çc][ãa]o da caixa",
     "reply": "", "noop": True, "only_subservices": ["limpeza_caixa_dagua"],
     "notes": "📊 2 msgs / 2 sessões. 🔴 LIMITE DE COBERTURA: duas caixas por "
              "acionamento."},
    {"step": "caixa_dagua_litros", "anchor": r"quantos litros tem cada caixa d.?[áa]gua",
     "reply": "{caixa_litros_opcao}", "requires": ["caixa_litros_opcao"],
     "fallback_adaptive": True, "only_subservices": ["limpeza_caixa_dagua"],
     "notes": "📊 2 msgs / 2 sessões. 1-Até 2.500 litros 2-Acima. 🔴 Vem do caso: "
              "o volume muda o equipamento e o tempo do serviço."},

    # ---- o galho do ELETRODOMÉSTICO ---------------------------------------
    {"step": "desgaste_natural_ou_nao",
     "anchor": r"o profissional ir[áa] verificar se o defeito [ée] desgaste natural",
     "reply": "", "noop": True,
     "only_subservices": ["eletrodomesticos", "maquina_de_lavar", "ar_condicionado"],
     "notes": "📊 2 msgs / 2 sessões. 🔴 EXCLUSÃO: mau uso e desgaste que não seja "
              "de componente NÃO são cobertos — e quem decide é o técnico, no local."},

    # ---- agendamento e desfecho -------------------------------------------
    {"step": "agendamento_para_confirma",
     "anchor": r"agendamento para:\s*[\s\S]{0,80}podemos continuar",
     "reply": "1",
     "constante_justificada": (
         "📊 2 msgs / 2 sessões. 1-Sim 2-Voltar. É a confirmação da data que o "
         "PRÓPRIO corredor escolheu no passo anterior — confirmar é confirmar o "
         "próprio dado."),
     "notes": "📊 2/2."},
    {"step": "protocolo_com_sucesso",
     "anchor": r"sua assist[êe]ncia foi solicitada com sucesso",
     "reply": "", "noop": True,
     "notes": "📊 É o DESFECHO. Quem lê o número é `capture_anchors.protocol`; o "
              "passo existe para o motor ficar calado enquanto a captura acontece."},

    # ---- 🔴 A LISTA COM MAIS DE UM ENDEREÇO -------------------------------
    # ⚠️ O `escolher_endereco_da_lista` do BLOCO 1 exige `2 - Voltar 3 - Sair`.
    #    📊 Estas telas têm DOIS ENDEREÇOS ("*1 -* R. ... *2 -* AV ..."), e ali
    #    "1" não é "o endereço da apólice": é o PRIMEIRO de dois.
    # 🔴 Escolher fixo manda o prestador para a casa errada. Vem do caso.
    {"step": "escolher_entre_dois_enderecos",
     "anchor": (r"^\*?1\s*-\*?\s*(?:r\.|av|rua|es |rod|tv)[\s\S]{0,200}"
                r"\*?2\s*-\*?\s*(?:r\.|av|rua|es |rod|tv)"),
     "reply": "{endereco_opcao}",
     # 🔴 SEM `requires` DE PROPOSITO -- e a ausencia e o achado.
     #
     #    Nenhuma das quatro origens serve aqui: nao e constante (a lista muda),
     #    nao se deriva (o relato nao diz "opcao 1"), nao se coleta (a corretora
     #    nao viu a tela para saber o que e a opcao 1) e o motor nao tem, para
     #    endereco, o equivalente do `pick_option_by_plate`.
     #
     #    A tela PRECISA ser lida. `fallback_adaptive` e o unico caminho honesto,
     #    e se o cerebro nao decidir, e handoff -- nunca posicao fixa, porque
     #    escolher errado manda o prestador para a casa de outra pessoa.
     #    Registrado em P-084-6 e P-084-9.
     "fallback_adaptive": True,
     "notes": "📊 3 telas / 4 sessões. 🔴 DOIS endereços de verdade, não endereço "
              "+ Voltar. Vem do caso; sem match seguro, o cérebro lê a tela e, "
              "falhando, é handoff — nunca posição fixa."},
]
ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = (
    list(ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"])
    + [dict(p) for p in _ALLIANZ_RESID_FOLHAS]
)
# 📊 "Apólice não encontrada com *CPF* ou *CNPJ* informado." — 1 sessão. Não é
#    passo: é o fim da linha. `_RESID_HANDOFF_TRIGGERS` já tem
#    `n[ãa]o localizamos`, que NÃO casa esta redação.
ALLIANZ_RESIDENCIAL_WHATSAPP_V1["handoff_triggers"] = (
    list(ALLIANZ_RESIDENCIAL_WHATSAPP_V1["handoff_triggers"])
    + [r"ap[óo]lice n[ãa]o encontrada"]
)


# ==========================================================================
# As DUAS rotas que ainda diziam NAO_RESPONDE (SPEC-084, 22/08/2026)
# ==========================================================================
#
# 🔴 `NAO_RESPONDE` é pior que `SEM_CORPUS`: significa que a seguradora tem
#    conversa no acervo e o corredor fica mudo nela.

# --------------------------------------------------------------------------
# PORTO · residencial · ELETRODOMÉSTICOS — 5 órfãs, e a URA não NUMERA
# --------------------------------------------------------------------------
PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = list(
    PORTO_RESIDENCIAL_WHATSAPP_V1["ura_steps"]) + [
    {"step": "eletro_familia",
     "anchor": r"o que voc[êe] precisa\?[\s\S]{0,120}convers[ãa]o de g[áa]s",
     "reply": "Conserto ou reparo",
     "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
     "constante_justificada": (
         "📊 1 msg / 1 sessão. As opções são 'Conserto ou reparo' · 'Conversão de "
         "gás' · 'Contratar instalação' · 'Não encontrei'. 🔴 Conversão de gás e "
         "contratar instalação são VENDA PARTICULAR, não apólice — e o corredor "
         "existe para acionar cobertura."),
     "notes": "📊 1 msg / 1 sessão."},

    # 🔴 O `^` É O QUE SEPARA DUAS PERGUNTAS IDÊNTICAS — controle do coletor:
    #    sem ele, a âncora casa 4 telas: as 3 de APARELHO e mais
    #    "Entendi. O conserto ou reparo é para o quê? Novo serviço / Retorno do
    #     prestador / Acompanhar um serviço" — que é outra decisão inteira.
    #    Com `^`, casa exatamente as 3.
    {"step": "eletro_categoria", "anchor": r"^o conserto ou reparo [ée] para o qu[êe]\s*\?",
     "reply": "{eletrodomestico_rotulo}", "fallback_adaptive": True,
     "only_subservices": ["eletrodomesticos", "maquina_de_lavar"],
     "notes": "📊 3 telas / 1 sessão. 🔴 A porto NÃO NUMERA os aparelhos — "
              "diferente da Allianz, onde 14 = Máquina de Lavar roupas. Aqui é "
              "RÓTULO, e ele é 'Máquina de lavar roupa' (SINGULAR)."},
    {"step": "conserto_novo_ou_retorno",
     "anchor": r"^entendi\. o conserto ou reparo [ée] para o qu[êe]",
     "reply": "Novo serviço",
     "constante_justificada": (
         "📊 1 msg / 1 sessão. 'Novo serviço' x 'Retorno do prestador' x "
         "'Acompanhar'. O corredor existe para ABRIR. ⚠️ Vem ANTES do "
         "`eletro_categoria` na lista porque as duas perguntas são a MESMA frase."),
     "notes": "📊 1/1."},

    # ⚠️ "Mais serviços" — 6 rótulos, ZERO fluxos. Não vira tecla: vira handoff.
    {"step": "mais_opcoes_lista",
     "anchor": (r"o que voc[êe] precisa\?[\s\S]{0,200}"
                r"(?:port[ãa]o de a[çc]o|telefonia e interfone)"),
     "reply": "", "noop": True,
     "notes": "📊 1 msg / 1 sessão. Portão de aço · Instalação de ventilador · "
              "Antenas · Telefonia e interfone · Mudança de mobiliário · Reparo em "
              "móveis. 🔴 SEIS rótulos e NENHUM fluxo observado — declarar tecla "
              "aqui é o defeito que `_ativar_vidros` proíbe. Ver PENDENCIAS."},
]

# --------------------------------------------------------------------------
# ALLIANZ · residencial · CONSULTA VETERINÁRIA — 8 órfãs, e o Pet tem ficha
# --------------------------------------------------------------------------
# 📊 1 sessão (c58a171a), e ela chega ao PROTOCOLO. O galho pede a ficha do
#    animal, e nenhum desses dados existe no produto hoje.
ALLIANZ_RESIDENCIAL_WHATSAPP_V1["subservices"]["consulta_veterinaria"][
    "required_slots"] = list(
    ALLIANZ_RESIDENCIAL_WHATSAPP_V1["subservices"]["consulta_veterinaria"][
        "required_slots"]) + ["pet_nome", "pet_raca", "pet_idade"]

ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"] = list(
    ALLIANZ_RESIDENCIAL_WHATSAPP_V1["ura_steps"]) + [
    {"step": "pet_especie", "anchor": r"atendimento para qual animal dom[ée]stico",
     "reply": "{pet_especie_opcao}", "requires": ["pet_especie_opcao"],
     "fallback_adaptive": True, "only_subservices": ["consulta_veterinaria"],
     "notes": "📊 1/1. 1-Cachorro 2-Gato 3-Outros."},
    {"step": "pet_nome", "anchor": r"qual o nome do pet",
     "reply": "{pet_nome}", "requires": ["pet_nome"], "fallback_adaptive": True,
     "only_subservices": ["consulta_veterinaria"], "notes": "📊 1/1."},
    {"step": "pet_raca", "anchor": r"^qual ra[çc]a\s*\?",
     "reply": "{pet_raca}", "requires": ["pet_raca"], "fallback_adaptive": True,
     "only_subservices": ["consulta_veterinaria"], "notes": "📊 1/1."},
    {"step": "pet_idade", "anchor": r"^qual a idade\s*\?",
     "reply": "{pet_idade}", "requires": ["pet_idade"], "fallback_adaptive": True,
     "only_subservices": ["consulta_veterinaria"],
     "notes": "📊 1/1. ⚠️ O `^` separa da idade do APARELHO, que é outra tela e "
              "outro subserviço."},
    {"step": "menu_outros_assuntos_sinistro",
     "anchor": r"precisando avisar ou acompanhar um sinistro",
     "reply": "", "noop": True,
     "notes": "📊 1 msg / 1 sessão. CARDÁPIO de outros assuntos (sinistro, "
              "carteirinha, apólice, pagamentos). Nenhum é assistência."},
]

_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    f"{p['playbook_id']}@v{p['version']}": p
    for p in (
        ALLIANZ_RESIDENCIAL_WHATSAPP_V1,
        ALLIANZ_AUTO_WHATSAPP_V1,
        PORTO_AUTO_WHATSAPP_V1,
        HDI_AUTO_WHATSAPP_V1,
        YELUM_AUTO_WHATSAPP_V1,
        TOKIO_AUTO_WHATSAPP_V1,
        ALFA_AUTO_WHATSAPP_V1,
        AZUL_AUTO_WHATSAPP_V1,
        BRADESCO_AUTO_WHATSAPP_V1,
        MAPFRE_AUTO_WHATSAPP_V1,
        ZURICH_AUTO_WHATSAPP_V1,
        HDI_RESIDENCIAL_WHATSAPP_V1,
        PORTO_RESIDENCIAL_WHATSAPP_V1,
        YELUM_RESIDENCIAL_WHATSAPP_V1,
    )
}


# ALFAIATE (SPEC-034 Onda 4): overlays noop auto-aplicados em runtime — avisos
# NOVOS da URA passam a ser ignorados sem deploy. Cache em memória, populado
# pela task periódica (refresh_overlay_cache); vazio = comportamento original.
_OVERLAY_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def set_overlay_cache(data: Dict[str, List[Dict[str, Any]]]) -> None:
    global _OVERLAY_CACHE
    _OVERLAY_CACHE = dict(data or {})


def get_playbook(playbook_ref: str) -> Optional[Dict[str, Any]]:
    ref = str(playbook_ref or "").strip()
    base = _PLAYBOOKS.get(ref)
    overlays = _OVERLAY_CACHE.get(ref) or []
    if not base or not overlays:
        return base
    # Cópia rasa com ura_steps NOVO — nunca mutar o playbook-fonte (duplicaria
    # overlays a cada chamada).
    merged = dict(base)
    extra = [
        {"step": f"overlay_noop_{i}", "anchor": str(o.get("anchor") or ""),
         "reply": "", "noop": True, "notes": str(o.get("note") or "Alfaiate")}
        for i, o in enumerate(overlays) if o.get("anchor")
    ]
    merged["ura_steps"] = list(base.get("ura_steps") or []) + extra
    return merged


def list_playbooks() -> List[str]:
    return sorted(_PLAYBOOKS.keys())


# ---------------------------------------------------------------------------
# Seleção de playbook e contato por seguradora (SPEC-031)
# ---------------------------------------------------------------------------

# Sinônimos de seguradora → chave canônica (a InfoCap pode devolver variações).
# Azul é do grupo Porto MAS tem WhatsApp e URA próprios → corredor próprio.
_INSURER_ALIASES = {
    "allianz": "allianz", "allianz seguros": "allianz",
    "porto": "porto", "porto seguro": "porto",
    "itau": "itau", "itau seguros": "itau",
    "azul": "azul", "azul seguros": "azul",
    "hdi": "hdi", "hdi seguros": "hdi",
    "yelum": "yelum", "liberty": "yelum", "liberty seguros": "yelum", "libe": "yelum",
    "tokio": "tokio", "tokio marine": "tokio", "tokyo": "tokio",
    "alfa": "alfa", "alfa seguradora": "alfa", "alfa seguros": "alfa",
    "bradesco": "bradesco", "bradesco seguros": "bradesco", "bradesco auto/re": "bradesco",
    "mapfre": "mapfre", "mapfre seguros": "mapfre",
    "zurich": "zurich", "zurich seguros": "zurich", "zurich santander": "zurich",
    # Vistas nas conversas reais da Resulta em 29/07/2026, durante a destilação
    # do histórico. Sem elas, "sompo seguros" e "seguros sura" viravam chaves
    # diferentes de "sompo" e "sura", e o filtro por seguradora perdia carta.
    "sompo": "sompo", "sompo seguros": "sompo",
    "sura": "sura", "seguros sura": "sura",
    "metlife": "metlife", "met life": "metlife",
    "axa": "axa", "axa seguros": "axa",
    "youse": "youse",
    "suhai": "suhai", "suhai seguradora": "suhai",
    "mitsui": "mitsui", "msig": "mitsui", "mitsui sumitomo": "mitsui",
    "akad": "akad", "akad seguros": "akad",
    "caixa": "caixa", "caixa seguradora": "caixa", "caixa seguros": "caixa",
    # 📊 Encontradas no acervo em 05/08/2026 varrendo `knowledge_cards`:
    # 52 chaves distintas, 35 fora desta tabela. Estas são SEGURADORAS de
    # verdade e estavam sobrevivendo pelo fallback `raw.split()[0]` — que
    # funciona por acidente em nome de uma palavra e falha em "sul america",
    # onde produzia a chave `sul` (duas cartas de previdência da SulAmérica
    # arquivadas sob uma sílaba). Esta tabela é a lista de quem É seguradora:
    # `curadoria_cartas` a usa para decidir o que pode ficar em `insurer_key`,
    # e o que não está aqui não é companhia — é prestadora, corretora ou ruído.
    "essor": "essor", "essor seguros": "essor",
    "ezze": "ezze", "ezze seguros": "ezze",
    "chubb": "chubb", "chubb seguros": "chubb",
    "generali": "generali", "generali seguros": "generali",
    "darwin": "darwin", "darwin seguros": "darwin",
    "berkley": "berkley", "berkley international": "berkley",
    "pottencial": "pottencial", "pottencial seguradora": "pottencial",
    "sulamerica": "sulamerica", "sul america": "sulamerica",
    "sul america seguros": "sulamerica", "sulamerica seguros": "sulamerica",
    "unimed": "unimed",
}


# QUEM OPERA A ASSISTÊNCIA DE QUEM.
#
# Isto NÃO é grafia alternativa — é fato de negócio: a carteira de auto do Itaú
# é operada pela infraestrutura da Porto, e o corredor de acionamento tem de
# apontar para lá. `test_spec031_auto_dispatch` cobre isso.
#
# Mas o Itaú vende vida e residencial em nome próprio, e um subagente
# destilando o lote 043 mostrou o efeito de misturar os dois usos: "uma regra
# específica do Itaú seria arquivada como Porto" — a mesma família do erro que
# atribuiu à Yelum o prazo de PIX da Youse.
#
# Uma tabela, duas leituras. ACIONAR pergunta "por onde eu ligo"; ARQUIVAR
# pergunta "de quem é esta regra". São perguntas diferentes e a resposta certa
# é diferente.
_OPERADO_POR = {"itau": "porto"}

# E a operação é POR CARTEIRA. 📊 O que a evidência diz é que a carteira de AUTO
# do Itaú roda na infraestrutura da Porto — nada foi observado sobre residencial.
# Enquanto só existia corredor residencial da Allianz, a distinção não aparecia.
# Com o corredor residencial da PORTO no ar, aplicar `_OPERADO_POR` a residencial
# mandaria uma apólice residencial do Itaú para o roteiro da Porto — exatamente
# o erro que a tabela acima descreve, com o sinal trocado.
_OPERADO_POR_LINHAS = {"itau": ("auto",)}


def normalize_insurer_key(insurer: str, para: str = "corredor") -> str:
    """Chave canônica da seguradora.

    `para="corredor"` (padrão): por onde se aciona. Aplica `_OPERADO_POR`.
    `para="conhecimento"`: de quem é a regra. NÃO aplica — uma carta do Itaú
    fica sob Itaú, senão o agente responde regra da Porto a segurado do Itaú.
    """
    # `_` e `-` viram espaço antes de comparar: "tokio_marine" chega assim de
    # importação antiga, e para o regex o sublinhado é letra — `\btokio\b` não
    # casaria, e a chave sobreviveria separada da `tokio` de todas as outras.
    raw = re.sub(r"[^a-z0-9]+", " ", _norm(insurer)).strip()
    # PALAVRA INTEIRA, não pedaço de palavra.
    #
    # Isto era `if alias in raw`. Com "axa" na lista, "caixa seguradora" virava
    # `axa` — duas seguradoras diferentes fundidas numa chave só, e o agente
    # respondendo regra da AXA para segurado da Caixa. Substring é aceitável
    # enquanto ninguém acrescenta um alias curto; o dia em que alguém
    # acrescenta, o erro é silencioso e sai errado para o cliente.
    def _final(chave: str) -> str:
        return _OPERADO_POR.get(chave, chave) if para == "corredor" else chave

    if raw in _INSURER_ALIASES:
        return _final(_INSURER_ALIASES[raw])
    for alias, key in _INSURER_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", raw):
            return _final(key)
    return _final(raw.split()[0]) if raw else ""


def resolve_playbook_ref(insurer: str, line_kind: str = "auto", channel: str = "whatsapp") -> Optional[str]:
    """Resolve o playbook_ref pela seguradora + linha. None se não houver."""
    line = str(line_kind or "auto").strip().lower()
    line = "residencial" if line in ("residencial", "residencia", "resid", "casa", "home") else line
    # Quem opera a assistência de quem vale POR CARTEIRA (ver `_OPERADO_POR_LINHAS`).
    key = normalize_insurer_key(insurer, para="conhecimento")
    operador = _OPERADO_POR.get(key)
    if operador and line in _OPERADO_POR_LINHAS.get(key, ()):
        key = operador
    for ref, pb in _PLAYBOOKS.items():
        if (pb.get("insurer_key") == key and pb.get("line_kind") == line
                and pb.get("channel") == str(channel or "whatsapp").strip().lower()):
            return ref
    return None


def insurer_contact_env_var(insurer: str, line_kind: str = "auto") -> str:
    """Nome do env com o contato (WhatsApp) da assistência da seguradora.
    Ex.: INSURER_CONTACT_PORTO_ASSISTENCIA. Allianz mantém o env legado."""
    key = normalize_insurer_key(insurer).upper() or "DESCONHECIDA"
    return f"INSURER_CONTACT_{key}_ASSISTENCIA"


def resolve_insurer_contact(insurer: str, env: Optional[Dict[str, str]] = None, line_kind: str = "auto") -> str:
    """Telefone da assistência da seguradora (só dígitos). Nunca hard-coded no
    playbook: vem de env/config da plataforma. Allianz tem fallback legado."""
    import os as _os

    env = env if env is not None else _os.environ
    candidates = [insurer_contact_env_var(insurer, line_kind)]
    if normalize_insurer_key(insurer) == "allianz":
        candidates.append("INSURER_CONTACT_ALLIANZ_ASSISTENCIA_24H")
    for var in candidates:
        val = "".join(ch for ch in str(env.get(var) or "") if ch.isdigit())
        if val:
            return val
    # Fallback: Registro de Seguradoras (SPEC-034 — números da planilha,
    # validados pela corretora). O env continua mandando quando definido.
    try:
        from app.services.insurer_registry import registry_whatsapp

        return "".join(ch for ch in registry_whatsapp(normalize_insurer_key(insurer)) if ch.isdigit())
    except Exception:  # noqa: BLE001
        return ""


def auto_subservice_menu_value(playbook: Dict[str, Any], subservice: str) -> str:
    """Opção/rótulo do menu da seguradora para o subserviço auto (guincho→'3' ou 'Guincho').

    Vazio quando a seguradora não tem menu OBSERVADO para aquele subserviço —
    e vazio significa handoff, nunca 'escolhe a primeira opção'."""
    sub = canonical_subservice(subservice)
    return str((playbook.get("subservice_menu_map") or {}).get(sub) or "")


def subservice_supported(playbook: Dict[str, Any], subservice: str) -> bool:
    """Esta seguradora tem corredor observado para este subserviço?

    False = não há evidência (📊 vidros em allianz/tokio/mapfre/yelum/hdi/alfa/
    bradesco, por exemplo) → o caso vira handoff humano com o motivo escrito.
    Nunca é convite para improvisar um menu.

    🔴 E DECLARAR O SUBSERVIÇO NÃO BASTA: SE O CORREDOR USA MENU, PRECISA DA
       TECLA — 22/08/2026.

    Esta função lia só `subservices`. 📊 Quando o menu da AZUL migrou em
    07/04/2026, "Troca de pneu" deixou de existir na tela e o
    `subservice_menu_map` ficou apontando `"3"` — uma tecla morta. Tirar a
    tecla errada, sozinho, deixaria o pior dos dois mundos: `pneu` seguiria
    "suportado", o corredor chegaria ao menu e **não teria o que digitar**.

    ⚠️ Antes ele digitava algo que a URA rejeita; depois, nada. Os dois são
       ruins, e nenhum é handoff — que é a resposta honesta quando não há
       rótulo observado.

    🔴 CONTROLE, medido sobre os 14 corredores antes de apertar a regra:
       exatamente **1** subserviço declarado ficaria sem tecla (`azul x pneu`).
       Os corredores residenciais de allianz/hdi/porto/yelum **não usam**
       `subservice_menu_map` — para eles a regra não se aplica, e a condição
       `if not mapa` é o que garante isso.
    """
    subs = playbook.get("subservices") or {}
    alvo = canonical_subservice(subservice)
    if alvo not in subs:
        return False
    mapa = playbook.get("subservice_menu_map") or {}
    if not mapa:
        # corredor sem menu de serviço: a rota se escolhe por outro caminho
        return True
    return alvo in mapa


def subservice_outcome(playbook: Dict[str, Any], subservice: str) -> str:
    """Como este corredor TERMINA: `abre` (vai até o protocolo) ou `encaminha`
    (a seguradora entrega formulário/orientação e o caso encerra resolvido).

    Subserviço inexistente devolve "" — não existe desfecho para trabalho que
    esta seguradora não faz por este canal."""
    sub = (playbook.get("subservices") or {}).get(canonical_subservice(subservice))
    if sub is None:
        return ""
    return str(sub.get("outcome") or OUTCOME_ABRE)


def subservice_referral(playbook: Dict[str, Any], subservice: str) -> Dict[str, Any]:
    """O encaminhamento declarado do subserviço (formulário/orientação), ou {}.

    Traz `client_message` (o que dizer ao segurado, sem inventar link nem prazo),
    `closes_as` e onde o link cai (`link_capture`)."""
    sub = (playbook.get("subservices") or {}).get(canonical_subservice(subservice)) or {}
    return dict(sub.get("referral") or {})


def detect_referral_step(playbook: Dict[str, Any], insurer_message: str) -> Optional[Dict[str, Any]]:
    """O passo de ENCAMINHAMENTO que casou com a mensagem da seguradora.

    É o espelho de `detect_finalize_anchor`, do outro lado do fluxo: em vez de
    'a seguradora vai abrir o serviço', diz 'a seguradora não vai abrir serviço
    nenhum aqui — ela entregou o caminho'. Quem chama decide encerrar o caso
    como resolvido-por-encaminhamento e repassar o `client_message` do
    subserviço ao segurado."""
    text = _norm(insurer_message)
    for step in playbook.get("ura_steps") or []:
        if not step.get("referral"):
            continue
        if re.search(step.get("anchor") or r"$^", text, re.IGNORECASE | re.DOTALL):
            return step
    return None


def render_opening_message(playbook: Dict[str, Any], subservice: str, slots: Dict[str, Any]) -> str:
    """Resumo estruturado do pedido para abrir a fase humana da seguradora (auto)."""
    template = playbook.get("opening_template")
    if not template:
        return "Olá"
    labels = playbook.get("subservice_labels") or {}
    data = {k: str(v) for k, v in (slots or {}).items()}
    data.setdefault("subservice_label", labels.get(str(subservice or "").lower(), "assistência 24h"))
    # Campos opcionais nunca quebram o template.
    for opt in ("veiculo_descricao", "titular_nome", "local_destino", "pessoa_no_local", "quando"):
        data.setdefault(opt, "-")
    try:
        return template.format_map({**{k: "-" for k in _optional_keys()}, **data})
    except Exception:  # noqa: BLE001
        return "Olá, preciso de assistência 24h para o veículo do nosso segurado."


def _optional_keys() -> List[str]:
    return [
        "subservice_label", "veiculo_placa", "veiculo_descricao", "titular_nome", "titular_cpf",
        "local_atual", "local_destino", "problema_descricao", "quando", "pessoa_no_local", "telefone_contato",
        "endereco_numero", "periodo_preferido",
    ]


def detect_finalize_anchor(playbook: Dict[str, Any], insurer_message: str) -> Optional[str]:
    """FREIO: retorna o padrão casado quando a seguradora vai CONFIRMAR/ABRIR o
    serviço. O motor pausa (needs_human) em vez de confirmar sozinho — o passo
    final (que despacha o prestador) exige aprovação da corretora."""
    text = _norm(insurer_message)
    for pattern in playbook.get("finalize_anchors") or []:
        if re.search(pattern, text, re.IGNORECASE):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Motor puro: match de URA, preenchimento de resposta, captura de âncoras
# ---------------------------------------------------------------------------

def match_ura_step(playbook: Dict[str, Any], insurer_message: str, subservice: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Primeiro passo de URA cuja âncora casa com a mensagem da seguradora.
    `only_subservices` restringe o passo a certos subserviços (a MESMA pergunta
    da URA pode exigir respostas diferentes por serviço)."""
    text = _norm(insurer_message)
    sub = canonical_subservice(subservice)  # 'pane seca' entra pelo caminho do guincho
    for step in playbook.get("ura_steps") or []:
        only = step.get("only_subservices")
        if only and sub not in [str(x).lower() for x in only]:
            continue
        if re.search(step.get("anchor") or r"$^", text, re.IGNORECASE | re.DOTALL):
            return step
    return None


_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
_STREET_RE = re.compile(
    r"\b(?:rua|r\.|av\.?|avenida|rod\.?|rodovia|estrada|travessa|tv\.?|alameda|al\.?|"
    r"servid[ãa]o|br-?\s?\d+|sc-?\s?\d+|pra[çc]a|largo|beco|via|linha)\b", re.IGNORECASE)

# RODOVIA NÃO TEM NÚMERO DE CASA — e é por isso que ela precisa de caminho próprio.
#
# 📊 03/08/2026: `"Rodovia BR-101, km 150, Palhoça - SC"` saía como
# rua `"Rodovia BR"`, **número `101`**, bairro `"km 150"`. O parser quebra o
# texto em `,` e `-`, e o hífen de `BR-101` é o mesmo caractere que separa
# segmentos: a designação da rodovia era partida ao meio, o número dela virava
# número de casa e o quilômetro virava bairro.
#
# Nada disso é "quase certo". `número 101` é o endereço de uma casa que existe
# em outra rua; o guincho sai com um destino errado e com confiança. E o defeito
# não era só da BR: `SC-401` quebrava igual, e `km` virava bairro até em rodovia
# com nome próprio ("Rod. Anhanguera, km 90").
#
# A regra: reconhecida a rodovia, `numero` e `bairro` ficam FORA do dict. Quem
# assume dali é o `fallback_adaptive` dos passos — que sabe perguntar. Não saber
# é um estado honesto; errar com confiança, não.
# FEDERAL e ESTADUAL têm regras DIFERENTES, e a diferença é `AP 302`.
#
# `AP` é o código do Amapá **e** a abreviação de apartamento. Uma regra única
# `<UF>[-\s]?\d{2,3}` leria "Rua X, 100, AP 302" como rodovia e devolveria um
# endereço sem número — trocando um erro por outro. Já `BR` não é abreviação de
# nada num endereço, então ele basta sozinho.
_RODOVIA_FEDERAL_RE = re.compile(r"\bBR[-\s]?\d{2,3}\b", re.IGNORECASE)
_RODOVIA_ESTADUAL_RE = re.compile(
    r"\b(?:" + "|".join(sorted(_UFS)) + r")[-\s]?\d{2,3}\b", re.IGNORECASE)
_RODOVIA_RE = re.compile(
    r"\b(?:BR|" + "|".join(sorted(_UFS)) + r")[-\s]?\d{2,3}\b", re.IGNORECASE)
_KM_RE = re.compile(r"\bkm\s*\.?\s*\d{1,4}(?:[.,]\d{1,3})?\b", re.IGNORECASE)
_VIA_RE = re.compile(r"\b(?:rod\.?|rodovia|estrada|via\s+expressa|anel\s+vi[áa]rio)\b",
                     re.IGNORECASE)


def _e_rodovia(raw: str) -> bool:
    """O texto descreve uma RODOVIA? Só então o caminho especial se abre.

    Código estadual sozinho não basta (`AP 302`): ele precisa de companhia —
    a palavra da via ou a quilometragem. `BR-101` basta.
    """
    if _RODOVIA_FEDERAL_RE.search(raw):
        return True
    apoio = bool(_VIA_RE.search(raw) or _KM_RE.search(raw))
    if _RODOVIA_ESTADUAL_RE.search(raw) and apoio:
        return True
    # Rodovia de nome próprio: "Rod. Anhanguera, km 90" não traz código nenhum.
    return bool(_KM_RE.search(raw) and _VIA_RE.search(raw))


def _endereco_de_rodovia(raw: str, out: Dict[str, str]) -> Dict[str, str]:
    """Rodovia: `rua` carrega a identificação inteira; `numero`/`bairro` NUNCA.

    A quilometragem fica em `rua` de propósito. Jogá-la fora seria trocar um
    erro por uma perda: `km 150` é a única coisa que diz ONDE na BR-101 a pessoa
    está, e sem ela o guincho tem 500 km de rodovia para procurar.
    """
    # Só a vírgula separa aqui. O hífen NÃO pode separar: ele é parte de `BR-101`.
    partes = [p.strip(" .") for p in raw.split(",") if p.strip(" .-")]
    if not partes:
        return out
    # UF no fim: "Palhoça - SC", "Palhoça SC" ou "SC" sozinha.
    cauda = re.split(r"\s+[-–]\s+|\s+", partes[-1].strip())
    if cauda and cauda[-1].upper() in _UFS:
        out["uf"] = cauda[-1].upper()
        resto = " ".join(cauda[:-1]).strip(" -–")
        if resto:
            partes[-1] = resto
        else:
            partes = partes[:-1]

    def _e_da_rodovia(p: str) -> bool:
        return bool(_RODOVIA_RE.search(p) or _KM_RE.search(p) or _VIA_RE.search(p))

    via = [p for p in partes if _e_da_rodovia(p)]
    if via:
        out["rua"] = ", ".join(via)
    # A cidade é o último segmento que NÃO descreve a rodovia. "sentido norte"
    # e "pista sul" descrevem a via e não são cidade — mas também não são
    # bairro, e por isso simplesmente não viram campo nenhum.
    sobra = [p for p in partes if p not in via
             and not re.fullmatch(r"(?i)\s*(?:sentido|pista|sent\.?)\s+\w+\s*", p)]
    if sobra:
        out["cidade"] = sobra[-1]
    return out


def parse_address_br(text: str) -> Dict[str, str]:
    """Heurística de endereço BR em texto livre → componentes para URAs que pedem
    rua/número/bairro/cidade/UF separados (Yelum/HDI/Allianz destino).

    Aceita formatos reais das conversas: "Rua B, 50, Sao Jose SC",
    "R. Abelardo Luz, 342 - Balneario, Florianópolis - SC, 88075-542",
    "Av Santa Tecla 2400, Bagé, RS". Campo não deduzido fica FORA do dict
    (o passo cai no cérebro adaptativo — nunca chuta)."""
    out: Dict[str, str] = {}
    raw = str(text or "").strip()
    if not raw:
        return out
    # UM ENDEREÇO É UMA LINHA.
    #
    # 03/08/2026: o pin de localização do WhatsApp passou a chegar como texto, e
    # ele traz a coordenada. Colada na mesma linha, `-48.5477` virava a CIDADE —
    # o parser quebra em `,` e `-`, e o último segmento é onde a cidade mora.
    # Uma cidade chamada "48.5477" não é uma dedução ruim; é uma invenção.
    # Ler só a primeira linha com conteúdo resolve a classe: qualquer rodapé
    # (coordenada, legenda, assinatura) deixa de virar campo de endereço.
    raw = next((l.strip() for l in raw.splitlines() if l.strip()), "")
    if not raw:
        return out
    m = re.search(r"\b(\d{5})-?(\d{3})\b", raw)
    if m:
        out["cep"] = f"{m.group(1)}-{m.group(2)}"
        raw = raw.replace(m.group(0), " ")
    # RODOVIA sai por outra porta (ver `_endereco_de_rodovia`): aqui embaixo o
    # hífen separa segmentos, e `BR-101` seria partido em "BR" + "101".
    #
    # Quando a porta abre está em `_e_rodovia`. Rodovia com nome e SEM km segue
    # pelo caminho urbano de propósito: ali um número no fim ainda costuma ser
    # número de imóvel, e trocar uma heurística boa por uma recusa não melhora
    # nada.
    if _e_rodovia(raw):
        return _endereco_de_rodovia(raw, out)
    parts = [p.strip(" .") for p in re.split(r"[,\-–]| - ", raw) if p.strip(" .-")]
    if not parts:
        return out
    # UF: token final de 2 letras válido (pode vir grudado na cidade: "Sao Jose SC").
    #
    # A BARRA SEPARA TANTO QUANTO O ESPAÇO — e ela é o formato mais comum de
    # todos: `Palhoça/SC`, `São José/SC`, `Florianópolis/SC`.
    #
    # 📊 05/08/2026, achado ao auditar a conferência de confirmação: sem a barra
    # aqui, `parse_address_br("R. das Flores, 250, Centro, Palhoça/SC")` devolvia
    # **cidade `"Palhoça/SC"` e nenhuma UF**. Dois estragos, e o segundo é o
    # caro: (1) a conferência comparava "Palhoça/SC" com "Palhoça" e REPROVAVA
    # uma confirmação legítima; (2) os passos que preenchem `{local_cidade}` e
    # `{destino_uf}` mandavam a cidade com a sigla colada para a URA, e a UF não
    # ia nunca — o passo caía no adaptativo por falta de um dado que estava ali.
    #
    # `_STREET_RE` e o resto continuam quebrando só em `,` e `-`: a barra entra
    # apenas nesta leitura de cauda, onde `100/A` (complemento) não chega.
    tail_tokens = re.split(r"[\s/]+", parts[-1].strip())
    if tail_tokens and tail_tokens[-1].upper() in _UFS:
        out["uf"] = tail_tokens[-1].upper()
        rest = " ".join(tail_tokens[:-1]).strip()
        if rest:
            parts[-1] = rest
        else:
            parts = parts[:-1]
    # Rua: primeiro segmento com cara de logradouro (ou o primeiro segmento).
    street_idx = next((i for i, p in enumerate(parts) if _STREET_RE.search(p)), 0)
    street = parts[street_idx]
    # Número embutido no segmento da rua ("Av Santa Tecla 2400" / "km 205").
    m = re.search(r"\s(?:n[ºo°.]?\s*)?(\d{1,5})$", street) or re.search(r"\bkm\s*(\d{1,4})\b", street, re.IGNORECASE)
    if m:
        out["numero"] = m.group(1)
        street = street[: m.start()].strip(" ,")
    out["rua"] = street
    rest = parts[street_idx + 1:]
    # Número como segmento próprio ("Rua B, 50, ...").
    if "numero" not in out and rest and re.fullmatch(r"(?:n[ºo°.]?\s*)?\d{1,5}(?:\s*km)?", rest[0], re.IGNORECASE):
        out["numero"] = re.sub(r"\D", "", rest[0])
        rest = rest[1:]
    rest = [p for p in rest if p]
    if len(rest) >= 2:
        out["bairro"] = rest[0]
        out["cidade"] = rest[-1]
    elif len(rest) == 1:
        out["cidade"] = rest[0]
    return out


def inject_address_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
    """Deriva slots de endereço decompostos a partir de local_atual/local_destino.
    Só preenche o que a heurística deduziu (faltante → adaptativo assume)."""
    for src, prefix in (("local_atual", "local"), ("local_destino", "destino")):
        parsed = parse_address_br(str(slots.get(src) or ""))
        for key, val in parsed.items():
            slots.setdefault(f"{prefix}_{key}", val)
    # Aliases usados pelos passos da Allianz (logradouro = rua).
    if slots.get("destino_rua"):
        slots.setdefault("destino_logradouro", slots["destino_rua"])
    return slots


# A SEGURADORA MOSTRA O DADO MASCARADO — E MASCARADO NÃO SE COMPARA COM `==`.
#
# Esta regra nasceu dentro de `pick_option_by_plate` (menu de veículos, 12/07) e
# saiu para cá porque a MESMA armadilha reaparece na conferência do resumo
# final: `"JC#-###9" == "JCL9A59"` dá **False** e reprovaria o veículo CERTO.
# Um segundo comparador escrito à mão ao lado deste seria a duplicação que a
# CLAUDE.md §5 proíbe — e, pior, os dois divergiriam no primeiro caractere de
# máscara novo que uma seguradora inventasse.
#
# Os quatro caracteres: `#` (Allianz/HDI/Yelum), `*`, `?` e `•`/`●` (bullets que
# a Porto e a Azul usam para esconder dígito). `*` entra aqui apesar de ser o
# negrito do WhatsApp: quem chama já recebeu o texto do campo, não a linha.
_CARACTERE_DE_MASCARA = "#*?•●"


def bate_com_mascara(mascarado: str, do_caso: str) -> Optional[bool]:
    """True / False / **None = não comparável** — e o `None` é o mais importante.

    Comprimentos diferentes NÃO são divergência: são ausência de base de
    comparação. Os dois erros clássicos que este tipo ternário fecha:

      `"JC#-###9" == "JCL9A59"`  → False  → reprovaria o veículo certo
      `"125" in "1253"`          → True   → aprovaria o endereço errado

    Pontuação e separador saem dos dois lados antes de comparar (`JC#-###9` e
    `JCL9A59` viram `JC####9` e `JCL9A59`, ambos de 7).
    """
    a = re.sub(rf"[^A-Za-z0-9{re.escape(_CARACTERE_DE_MASCARA)}]", "", str(mascarado or "")).upper()
    b = re.sub(r"[^A-Za-z0-9]", "", str(do_caso or "")).upper()
    if not a or not b or len(a) != len(b):
        return None
    return all(ca in _CARACTERE_DE_MASCARA or ca == cb for ca, cb in zip(a, b))


def pick_option_by_plate(insurer_message: str, placa: str) -> str:
    """Escolhe a opção do menu de veículos pela PLACA MASCARADA da URA.
    Ex.: '1 - 2500, placa JD#-###2 / 2 - HILUX SW4, placa JC#-###9' com placa
    do caso JCL9A59 → '2' (prefixo JC e final 9 casam). '' = sem match seguro.

    A comparação em si mora em `bate_com_mascara`. Aqui ficou só o que é DESTE
    passo: achar as opções na tela e nunca chutar veículo (`None` — comprimento
    diferente — e `False` caem juntos no mesmo `continue`, e duas opções que
    casam também devolvem '')."""
    case = re.sub(r"[^A-Z0-9]", "", str(placa or "").upper())
    if not case:
        return ""
    matches = []
    for opt, masked in re.findall(r"(\d+)\s*-\s*[^\n]*?placa\s+([A-Z0-9#\-]+)", str(insurer_message), re.IGNORECASE):
        if bate_com_mascara(masked, case) is True:
            matches.append(opt)
    return matches[0] if len(matches) == 1 else ""


def _format_phone_br(value: str) -> str:
    """Formata dígitos no padrão estrito '(dd) 99999-9999' (a Azul REJEITA outro)."""
    d = "".join(ch for ch in str(value or "") if ch.isdigit())
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return str(value)


def render_reply(step: Dict[str, Any], slots: Dict[str, Any]) -> Dict[str, Any]:
    """Resposta do passo com slots aplicados. Slot faltante -> blocker (nunca chuta)."""
    template = str(step.get("reply") or "")
    missing = [f for f in (step.get("requires") or []) if not str(slots.get(f) or "").strip()]
    if missing:
        return {"ok": False, "missing": missing, "reply": None}
    try:
        reply = template.format(**{k: str(v) for k, v in slots.items()})
    except KeyError as exc:  # placeholder sem slot
        return {"ok": False, "missing": [str(exc).strip("'")], "reply": None}
    if step.get("format") == "phone_br":
        reply = _format_phone_br(reply)
    return {"ok": True, "missing": [], "reply": reply}


# ---------------------------------------------------------------------------
# FORMULÁRIO NATIVO: montar a resposta por código
# ---------------------------------------------------------------------------
# `render_reply` responde uma tela de texto. Isto responde uma tela de APP: em
# vez de uma string, um objeto com o id de cada opção — o `paramsJSON` que o
# WhatsApp Flow espera de volta.
#
# É PURO: entra schema + slots, sai dicionário. Sem rede, sem banco, sem hora.
# Dá para provar offline, e é por isso que o freio abaixo é confiável.


def native_flow(playbook: Dict[str, Any], flow_id: str) -> Optional[Dict[str, Any]]:
    """O schema do formulário nativo daquele `flow_id`, ou None.

    Indexado por `flow_id` porque é o que a seguradora manda (o parser de
    interativas já o entrega em `interactive.flow.flow_id`) — e porque duas
    seguradoras da mesma família apontam para o MESMO registro."""
    return (playbook.get("native_flows") or {}).get(str(flow_id or "").strip()) or None


def detect_native_flow(playbook: Dict[str, Any], insurer_message: str) -> Optional[Dict[str, Any]]:
    """O flow cuja mensagem de ABERTURA casa com a mensagem da seguradora.

    Serve ao caso em que o `flow_id` não chegou (mensagem só com o corpo): a
    frase que abre o formulário é estável e está guardada no schema. Sem
    `prompt_anchor` declarado, o flow não é adivinhado."""
    text = _norm(insurer_message)
    for flow in (playbook.get("native_flows") or {}).values():
        anchor = flow.get("prompt_anchor")
        if anchor and re.search(anchor, text, re.IGNORECASE | re.DOTALL):
            return flow
    return None


def _flow_components(flow_schema: Dict[str, Any]):
    for screen in flow_schema.get("screens") or []:
        for comp in screen.get("components") or []:
            if comp.get("name"):
                yield screen, comp


def _flow_vazio(valor: Any) -> bool:
    """Vazio é ausência de resposta. `False` é uma RESPOSTA."""
    if isinstance(valor, bool):
        return False
    if valor is None:
        return True
    if isinstance(valor, (list, tuple, set)):
        return not [v for v in valor if not _flow_vazio(v)]
    return not str(valor).strip()


def _flow_visivel(comp: Dict[str, Any], parcial: Dict[str, Any]) -> tuple:
    """(visível?, é condicional?) do componente, dadas as respostas já montadas.

    Três casos, e o do meio é o que importa:
      - sem `visible_if`            → visível, direto;
      - `${form.X} == 'v'`          → dá para avaliar: X já está montado, ou não;
      - `${data.X}`, ou X ainda sem resposta → INDETERMINADO.

    Indeterminado conta como VISÍVEL. É de graça: se X não foi respondido, X já
    está em `missing` e o caso já está travado — incluir o dependente só entrega
    a pergunta inteira de uma vez, em vez de devolvê-la de novo na rodada
    seguinte. Tratar como invisível é que seria caro: omitiria, calado, um campo
    que o formulário talvez esteja exigindo."""
    cond = comp.get("visible_if")
    if not cond:
        return True, False
    if cond.get("kind") == "form":
        campo = str(cond.get("field") or "")
        if campo not in parcial:
            return True, True  # indeterminado
        return str(parcial.get(campo)) == str(cond.get("equals")), False
    return True, True  # ${data.*}: só o servidor da seguradora sabe


def _resolver_opcao_de_flow(comp: Dict[str, Any], bruto: Any) -> Optional[str]:
    """id da opção para o valor do caso. `None` = NÃO reconhecido — e não
    reconhecido nunca vira o padrão (ver `montar_resposta_de_flow`)."""
    if isinstance(bruto, bool):
        bruto = "sim" if bruto else "nao"
    raw = str(bruto).strip()
    if not raw:
        return None
    options = comp.get("options") or []
    for o in options:  # 1) o caso já fala em id
        if raw == str(o.get("id")):
            return str(o.get("id"))
    token = _norm(raw).strip()
    for o in options:  # 2) título exato — opção SEM título não casa com nada
        titulo = _norm(o.get("title") or "").strip()
        if titulo and token == titulo:
            return str(o.get("id"))
    alias = (comp.get("aliases") or {}).get(token)  # 3) apelido declarado
    if alias:
        return str(alias)
    if len(token) >= 4:  # 4) contido em UM título só (dois = ambíguo = None)
        hits = [str(o.get("id")) for o in options
                if _norm(o.get("title") or "").strip() and token in _norm(o.get("title") or "")]
        if len(hits) == 1:
            return hits[0]
    return None


def montar_resposta_de_flow(flow_schema: Dict[str, Any], slots: Dict[str, Any]) -> Dict[str, Any]:
    """Monta o `paramsJSON` de resposta do formulário nativo a partir dos slots.

    Devolve::

        {"ok": bool, "flow_id": str, "flow_name": str,
         "params": dict | None,        # None quando ok=False — NUNCA parcial
         "missing": [nome_do_campo],   # mesma forma de `render_reply`
         "missing_detail": [{campo, pergunta, motivo, valor_recebido, opcoes,
                             condicional}],
         "defaults_used": [nome_do_campo]}

    TRÊS REGRAS, e as três existem porque formulário meio preenchido é pior que
    formulário nenhum — o primeiro despacha o equipamento errado, o segundo
    chama um humano:

    1. **Todo campo `required` visível precisa de valor.** Faltando um,
       `ok=False` e `params=None`. Não existe resposta parcial.
    2. **Padrão só cobre AUSÊNCIA.** Se o slot tem valor e ele não casa com
       nenhuma opção, isso é `valor_nao_reconhecido` — vira `missing`, não vira
       o padrão. É o que impede um caso que diz "gestante" (📊 opção cujo título
       veio VAZIO na captura) de ser silenciosamente rebaixado para "Nenhuma das
       anteriores".
    3. **Só se responde o que a tela mostra.** Campo cuja condição de
       visibilidade é FALSA não entra na resposta nem na lista de faltantes.

    O `flow_token` NÃO sai daqui: ele é da sessão, muda a cada conversa, e quem
    o injeta é o transporte na hora do envio. Manter a função pura é o que
    permite provar tudo isto offline."""
    slots = slots or {}
    params: Dict[str, Any] = {}
    missing: List[str] = []
    detail: List[Dict[str, Any]] = []
    defaults_used: List[str] = []

    def _falta(comp: Dict[str, Any], motivo: str, valor: Any = None, condicional: bool = False) -> None:
        missing.append(str(comp.get("name")))
        detail.append({
            "campo": str(comp.get("name")),
            "pergunta": str(comp.get("label") or ""),
            "motivo": motivo,
            "valor_recebido": valor,
            "condicional": condicional,
            "opcoes": [{"id": str(o.get("id")), "titulo": str(o.get("title") or "")}
                       for o in comp.get("options") or []],
        })

    for _screen, comp in _flow_components(flow_schema):
        nome = str(comp.get("name"))
        visivel, condicional = _flow_visivel(comp, params)
        if not visivel:
            continue

        # O caso pode falar o nome do CAMPO (quem já conhece o flow) ou o nome do
        # SLOT (o vocabulário do corredor). Os dois valem; o campo tem precedência.
        bruto = slots.get(nome)
        if _flow_vazio(bruto):
            bruto = slots.get(str(comp.get("slot") or ""))

        if _flow_vazio(bruto):
            padrao = comp.get("default")
            if padrao is not None:
                params[nome] = list(padrao) if isinstance(padrao, (list, tuple)) else padrao
                defaults_used.append(nome)
            elif comp.get("required"):
                _falta(comp, "sem_valor", None, condicional)
            continue

        if comp.get("multiple"):
            itens = bruto if isinstance(bruto, (list, tuple, set)) else re.split(r"[;,/|]|\be\b", str(bruto))
            ids: List[str] = []
            nao_reconhecidos: List[str] = []
            for item in itens:
                if _flow_vazio(item):
                    continue
                oid = _resolver_opcao_de_flow(comp, item)
                if oid:
                    ids.append(oid)
                else:
                    nao_reconhecidos.append(str(item).strip())
            if nao_reconhecidos:
                _falta(comp, "valor_nao_reconhecido", nao_reconhecidos, condicional)
                continue
            ids = list(dict.fromkeys(ids))
            nenhuma = comp.get("none_option")
            # "Nenhuma das opções" junto de uma característica real é contradição
            # da coleta, não do formulário: o fato positivo vence.
            if nenhuma and len(ids) > 1 and nenhuma in ids:
                ids = [i for i in ids if i != nenhuma]
            if not ids:
                if comp.get("required"):
                    _falta(comp, "sem_valor", None, condicional)
                continue
            params[nome] = ids
            continue

        oid = _resolver_opcao_de_flow(comp, bruto)
        if not oid:
            _falta(comp, "valor_nao_reconhecido", bruto, condicional)
            continue
        params[nome] = oid

    ok = not missing
    return {
        "ok": ok,
        "flow_id": str(flow_schema.get("flow_id") or ""),
        "flow_name": str(flow_schema.get("flow_name") or ""),
        "params": params if ok else None,
        "missing": missing,
        "missing_detail": detail,
        "defaults_used": defaults_used,
    }


def detect_handoff_trigger(playbook: Dict[str, Any], insurer_message: str) -> Optional[str]:
    text = _norm(insurer_message)
    for pattern in playbook.get("handoff_triggers") or []:
        if re.search(pattern, text, re.IGNORECASE):
            return pattern
    return None


def extract_capture_anchors(playbook: Dict[str, Any], insurer_message: str) -> Dict[str, Any]:
    """Protocolo/senha/agendamento SOMENTE por âncora real (nunca inventados)."""
    anchors = playbook.get("capture_anchors") or {}
    text = _norm(insurer_message)
    out: Dict[str, Any] = {}
    m = re.search(anchors.get("protocol") or r"$^", text, re.IGNORECASE)
    if m:
        out["protocol"] = m.group(1)
    m = re.search(anchors.get("password") or r"$^", text, re.IGNORECASE | re.DOTALL)
    if m:
        out["password"] = m.group(1)
    m = re.search(anchors.get("eta") or r"$^", text, re.IGNORECASE)
    if m:
        out["eta_minutes"] = m.group(1)
    # 🔴 O CARIMBO DE ENTRADA — 22/08/2026, e ele É LIDO AQUI de propósito.
    #
    # 📊 A tokio manda "Seu protocolo de atendimento é 68977599" no turno 3
    #    de 8 a 11, ANTES de qualquer escolha de serviço, em 7 de 7 sessões. Isso
    #    é o número do CHAT, não do chamado — e `_ANCORA_DE_PROTOCOLO` o colhia
    #    como `protocol`, fazendo o corredor encerrar com "assistência aberta,
    #    protocolo 68977599" enquanto **nada foi aberto**.
    #
    # ⚠️ Declarar `ticket_de_entrada` no corredor e não lê-lo aqui seria repetir,
    #    na mesma função, o defeito descrito logo abaixo. Por isso o leitor nasce
    #    junto com a chave, e o teste que o guarda chama o MOTOR.
    m = re.search(anchors.get("ticket_de_entrada") or r"$^", text, re.IGNORECASE)
    if m:
        out["ticket_de_entrada"] = m.group(1)
    # 🔴 O AGENDAMENTO ERA DECLARADO E NUNCA LIDO — 21/08/2026.
    #
    # `schedule_agendado` existe no corredor residencial desde 18/08, com duas
    # redações medidas e um teste de 72 asserções em volta. E esta função lia
    # cinco chaves — `protocol`, `password`, `eta`, `schedule`, `tracking_link`
    # — e **nunca essa**.
    #
    # O teste passava porque chamava o regex direto, com helper próprio, sem
    # passar pelo motor. É o corolário do §9.3 que faltava escrever:
    # **teste de corredor tem de chamar o MOTOR; teste que chama o regex não
    # guarda nada.**
    #
    # 📊 O custo, no acionamento validado de 19/08: a Clarissa recebeu
    # "Prontinho! ✅ Sua assistência foi aberta" — sem data e sem período.
    # Exatamente o sintoma que o comentário da âncora diz evitar.
    #
    # A ordem importa: `schedule` primeiro (auto), e a residencial só entra se
    # a de auto não casou — assim nenhum corredor de auto muda de comportamento.
    sched = anchors.get("schedule")
    if sched:
        m = re.search(sched, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) >= 3:
                out["schedule"] = {"day": m.group(1), "from": m.group(2), "to": m.group(3)}
            else:  # âncora de auto: dia (+ hora opcional)
                out["schedule"] = {"day": m.group(1), "at": (m.group(2) if len(groups) >= 2 else None)}
    if "schedule" not in out:
        # 🔴 A JANELA DA PORTO — P-084-8. Ela traz DIA e FAIXA DE HORA, e é a
        #    última mensagem útil do acionamento. Sem este leitor, a chave
        #    `schedule_porto` seria mais uma declarada e nunca lida — o defeito
        #    que este arquivo já pagou com `schedule_agendado` e com
        #    `ticket_de_entrada`. O leitor nasce junto com a chave.
        porto = anchors.get("schedule_porto")
        if porto:
            m = re.search(porto, text, re.IGNORECASE)
            if m:
                out["schedule"] = {"day": m.group(1), "from": m.group(2),
                                   "to": m.group(3)}
    if "schedule" not in out:
        agendado = anchors.get("schedule_agendado")
        if agendado:
            m = re.search(agendado, text, re.IGNORECASE)
            if m:
                g = m.groups()
                out["schedule"] = {
                    "day": (g[0] or "").strip(" ,.-*"),
                    "periodo": ((g[1] if len(g) >= 2 else "") or "").strip(" ,.-*"),
                }
    link = anchors.get("tracking_link")
    if link:
        m = re.search(link, insurer_message, re.IGNORECASE)  # texto ORIGINAL (URL preserva caixa)
        if m:
            out["tracking_link"] = m.group(1)
    return out


# O SENTINELA DE HANDOFF — um nome só, para não virar "campo que falta".
#
# `missing_slots_for_subservice` devolve isto quando a seguradora NÃO faz este
# trabalho por este canal. Não é um dado ausente: é um caso que sai do corredor
# e vai para gente. Quem trata `missing_slots` como lista de campos precisa
# comparar com ESTA constante, e não com a string escrita à mão — foi a string
# solta que deixou o LLM perguntando ao segurado o "subservico_invalido" dele.
SUBSERVICO_INVALIDO = "subservico_invalido"


def missing_slots_for_subservice(playbook: Any, subservice: str, slots: Dict[str, Any]) -> List[str]:
    """O que ainda falta para acionar. `[SUBSERVICO_INVALIDO]` quando esta
    seguradora não faz este trabalho por este canal — que é handoff, não bloqueio
    de coleta.

    Aceita o playbook OU o `playbook_ref` (string). A ficha do atendente, em
    `graph.py::_slots_obrigatorios_do_caso`, passa o ref: com a assinatura antiga
    isso levantava AttributeError dentro do `try` do chamador e a ficha ficava
    permanentemente sem a linha "o que falta" — falha silenciosa, verde no CI."""
    if isinstance(playbook, str):
        playbook = get_playbook(playbook) or {}
    sub = ((playbook or {}).get("subservices") or {}).get(canonical_subservice(subservice))
    if not sub:
        return [SUBSERVICO_INVALIDO]

    faltando = [f for f in sub.get("required_slots") or [] if not str(slots.get(f) or "").strip()]

    # O QUE OS PASSOS EXIGEM TAMBÉM CONTA.
    #
    # `required_slots` é a lista escrita à mão. Mas os passos de URA declaram
    # `requires` por conta própria, e as duas listas divergiam em silêncio.
    #
    # 📊 03/08/2026: `pessoa_no_local` é exigido por três playbooks (HDI, Yelum,
    # Azul) e não está em `required_slots` de subserviço nenhum. O efeito não era
    # uma recusa honesta — era uma MENTIRA: a sessão nascia `ready_to_send`, o
    # acionamento começava, e o corredor travava no meio da conversa, com a URA
    # rodando e o cronômetro correndo.
    #
    # Passo com `fallback_adaptive` fica de fora: ali a falta é prevista, e o
    # cérebro responde. O que entra aqui é só o que trava de verdade.
    #
    # Consertar o gate, e não os três passos, fecha a classe inteira: qualquer
    # `requires` novo passa a ser cobrado ANTES, por construção.
    alvo = canonical_subservice(subservice)
    for passo in (playbook or {}).get("ura_steps") or []:
        if passo.get("fallback_adaptive") or passo.get("noop"):
            continue
        only = passo.get("only_subservices")
        if only and alvo not in [str(x).lower() for x in only]:
            continue
        for campo in passo.get("requires") or []:
            # O que o MOTOR preenche não se cobra do cliente.
            #
            # `tipo_servico_opcao`, `servico_opcao`, `telefone_adicionar_opcao`:
            # todos são escolha de MENU, derivada do `subservice_menu_map` por
            # `new_dispatch_session`. Cobrá-los aqui faria o produto perguntar ao
            # segurado qual botão apertar na URA da seguradora — que é a pergunta
            # que o corredor existe para não fazer.
            #
            # O sufixo é a regra, e não uma lista: lista diverge, sufixo não.
            # Quem injeta é `insurer_dispatch_service._slots_com_padrao_do_motor`.
            if campo.endswith("_opcao"):
                continue
            if campo not in faltando and not str(slots.get(campo) or "").strip():
                faltando.append(campo)
    return faltando


# ===========================================================================
# A CONFERÊNCIA DA CONFIRMAÇÃO — o único ponto irreversível do produto
# ===========================================================================
#
# Todo o resto do corredor se conserta na mensagem seguinte. Esta não: depois do
# "sim" existe um guincho na rua e uma pessoa esperando no lugar que a
# seguradora escreveu, não no lugar onde ela está.
#
# 📊 Medido em 05/08/2026 contra o motor real, com `DISPATCH_FINALIZE_MODE=live`
# (o padrão desde 04/08):
#
#     o caso diz .......... Rua Doutor Fúlvio Aducci, 1235
#     o resumo da URA diz . Rua Doutor Fúlvio Aducci, 1253
#     o motor respondeu ... "1"      ← CONFIRMOU
#
# Três caracteres trocados, e o guincho sai para uma casa que EXISTE, na rua
# certa, com a pessoa errada atendendo a porta.
#
# A conferência já existia — como PROSA, dentro de `_AUTO_HUMAN_PHASE_GUIDANCE`:
# *"antes de confirmar, confira (1) placa e veículo (2) o serviço (3) o endereço
# de origem (4) o destino"*. Um modelo lendo "1253" logo abaixo de "1235"
# concorda com facilidade. Texto no prompt é PEDIDO, não verificação.
#
# 📊 E o caminho principal nem é a LLM: quem responde a tela de confirmação é o
# passo determinístico do corredor — `confirmar_atendimento` → "1",
# `confirmar_solicitacao` → "Confirmar solicitação", `confirmar_abertura` →
# "Sim". Um guarda que morasse dentro de `guard_human_phase_reply` (que fiscaliza
# o RASCUNHO da LLM) não protegeria justamente quem mais dispara. Por isso o
# bloco é PURO aqui, e o gancho fica no choke point por onde os dois passam.
#
# A decisão do Founder que este desenho obedece: **o agente confirma sozinho**,
# sem aprovação humana. Então a proteção não pode ser "não confirme" — tem de
# ser CONFERIR ANTES. É por isso que campo ausente não reprova nada (ver
# `conferir_confirmacao`): tratar ausência como erro faria o agente nunca
# confirmar, que é o oposto do que foi decidido.

# As etiquetas com que as seguradoras escrevem cada campo do resumo.
_ETIQUETAS_DO_RESUMO = (
    ("placa", r"placa"),
    ("veiculo", r"ve[ií]culo|modelo|autom[óo]vel|carro"),
    ("servico", r"servi[çc]o|assist[êe]ncia solicitada|atendimento solicitado|tipo de atendimento"),
    ("origem", r"origem|endere[çc]o(?: de origem| do local| atual)?|local do ve[íi]culo|"
               r"local de atendimento|onde est[áa]"),
    ("destino", r"destino|local de destino|para onde|oficina"),
)
_TODOS_OS_ROTULOS = r"|".join(p for _, p in _ETIQUETAS_DO_RESUMO)


def ler_resumo(texto: str) -> Dict[str, str]:
    """`{campo: valor}` do que a seguradora ESCREVEU. Campo ausente fica fora."""
    achados: Dict[str, str] = {}
    # UMA ETIQUETA TERMINA ONDE A PRÓXIMA COMEÇA — e não no fim da linha.
    #
    # 📊 Sem esta fronteira, `*Serviço:* Encanador *Origem:* Rua B, 50` devolvia
    # servico = "Encanador Origem: Rua B, 50": o valor de um campo engolia o
    # campo seguinte. Um serviço assim não casa palavra nenhuma da tabela, e a
    # conferência deixava de comparar justamente o que tinha acabado de ler.
    for linha in re.sub(r"\*", "", str(texto or "")).splitlines():
        for campo, padrao in _ETIQUETAS_DO_RESUMO:
            if campo in achados:
                continue
            m = re.search(rf"(?i)\b(?:{padrao})\s*:\s*(.+?)(?=\s+(?:{_TODOS_OS_ROTULOS})\s*:|\s*$)", linha)
            if m and m.group(1).strip():
                achados[campo] = m.group(1).strip()
    return achados


# Linha de OPÇÃO não é linha de dado: "Botão 1: Agora" tem dois-pontos e não
# resume coisa nenhuma. 📊 Sem esta exclusão, a tela "agora ou prefere agendar"
# da família HDI/Yelum — que não tem resumo NENHUM — era contada como um resumo
# de 3 campos, e o corredor se declarava "resumo ilegível" na tela mais comum
# que ele tem.
_LINHA_DE_OPCAO = r"^\s*(?:bot[ãa]o|op[çc][ãa]o)\s*\d"


def parece_resumo(texto: str) -> bool:
    """Tem CARA de resumo: 3+ pares `etiqueta: valor` que não sejam opções."""
    linhas = [l for l in re.sub(r"\*", "", str(texto or "")).splitlines()
              if not re.search(_LINHA_DE_OPCAO, l, re.IGNORECASE)]
    return len([l for l in linhas
                if re.search(r"^\s*[A-Za-zÀ-ÿ][^:\n]{2,30}\s*:\s*\S", l)]) >= 3


# ---------------------------------------------------------------------------
# O "sim" sai das OPÇÕES DA PRÓPRIA TELA, nunca de uma lista fixa de palavras
# ---------------------------------------------------------------------------
#
# "Agora" é o sim na Yelum ("precisa agora ou prefere agendar?") e não quer
# dizer nada na Porto. Lista fixa de palavras afirmativas erra nas duas pontas.
_ROTULO_AFIRMATIVO = (r"\bsim\b|confirm|prosseguir|continuar|correto|de acordo|isso mesmo|"
                      r"\bagora\b|\bok\b|pode (?:seguir|abrir|enviar)")
_ROTULO_NEGATIVO = (r"\bn[ãa]o\b|sair|cancel|reinici|alterar|mudar|corrigir|voltar|editar|agendar|"
                    r"outro momento|desisti")


def opcoes_da_tela(texto: str) -> List[Tuple[str, str]]:
    """`[(tecla, rótulo)]` das opções que a tela oferece. Tecla '' = só rótulo.

    Os três formatos reais: `*1 -* Sim` (Allianz), `Botão 1: Agora` (HDI/Yelum)
    e a LISTA sem número da Porto/Azul, em que cada linha curta é uma opção e a
    resposta válida é o rótulo inteiro (dígito é rejeitado por aquele bot)."""
    plano = re.sub(r"\*", "", str(texto or ""))
    achados: List[Tuple[str, str]] = []
    for m in re.finditer(r"(?im)^\s*(?:bot[ãa]o\s*)?(\d{1,2})\s*[-:.)]\s*(.+?)\s*$", plano):
        achados.append((m.group(1), m.group(2)))
    for m in re.finditer(r"(?i)\b(?:bot[ãa]o|op[çc][ãa]o)\s*(\d{1,2})\s*:\s*([^\n]+)", plano):
        achados.append((m.group(1), m.group(2).strip()))
    if not achados:
        for linha in plano.splitlines():
            linha = linha.strip()
            if linha and len(linha) <= 40 and not linha.endswith("?") and ":" not in linha:
                achados.append(("", linha))
    return achados


def _sentido_do_rotulo(rotulo: str) -> Optional[bool]:
    baixo = str(rotulo or "").lower()
    if re.search(_ROTULO_NEGATIVO, baixo):
        return False
    if re.search(_ROTULO_AFIRMATIVO, baixo):
        return True
    return None


def e_afirmativa(rascunho: str, tela: str) -> bool:
    """O rascunho quer dizer SIM *nesta tela*?

    Fail-closed ao contrário do habitual, e de propósito: quando não dá para
    classificar, devolve **True**. Numa tela de confirmação, tratar o
    desconhecido como um "sim" só faz a conferência rodar; o contrário deixaria
    passar exatamente o caso que se quer pegar.
    """
    r = str(rascunho or "").strip()
    if not r:
        return False
    opcoes = opcoes_da_tela(tela)
    if re.fullmatch(r"\d{1,2}", r):
        for tecla, rotulo in opcoes:
            if tecla == r:
                v = _sentido_do_rotulo(rotulo)
                return True if v is None else v
        return True
    baixo = r.lower()
    for _tecla, rotulo in opcoes:
        rl = rotulo.lower().strip()
        if rl and (rl in baixo or baixo in rl):
            v = _sentido_do_rotulo(rotulo)
            if v is not None:
                return v
    v = _sentido_do_rotulo(r)
    return True if v is None else v


# ---------------------------------------------------------------------------
# A conferência dos quatro campos
# ---------------------------------------------------------------------------
_PALAVRAS_DE_SERVICO = {
    "guincho": r"guincho|reboque|rebocar|remo[çc][ãa]o",
    "bateria": r"bateria|carga|pane el[ée]tric",
    "pneu": r"pneu|borrach|estepe",
    "chaveiro": r"chave",
    "vidros": r"vidro|para-?brisa|retrovisor|farol",
    "eletricista": r"el[ée]tric",
    "encanador": r"encanad|hidr[áa]ul|vazamento",
    "desentupimento": r"desentup",
}
# "Rua"/"Avenida" não distinguem endereço nenhum: comparar tokens sem tirá-los
# faria "Rua A" e "Rua B" terem interseção e passarem como o mesmo lugar.
_RUIDO_DE_LOGRADOURO = (r"^(rua|r|av|avenida|rod|rodovia|estrada|travessa|tv|alameda|al|via|"
                        r"praca|pra[çc]a|linha|servid[ãa]o)$")


def _tokens_comparaveis(texto: str) -> List[str]:
    limpo = re.sub(r"[^a-z0-9 ]", " ", _norm(texto).strip())
    return [t for t in limpo.split() if len(t) >= 3 and not re.fullmatch(_RUIDO_DE_LOGRADOURO, t)]


def _so_digitos(v: str) -> str:
    return re.sub(r"\D", "", str(v or "")).lstrip("0")


def _conferir_endereco(campo: str, do_resumo: str, do_caso: str, parser) -> List[Dict[str, str]]:
    """Divergências componente a componente. Só compara o que existe nos DOIS.

    O NÚMERO se compara por DÍGITOS EXATOS, nunca por `in`: `"125" in "1253"` é
    True, e foi exatamente essa a família do defeito que pagou este bloco.
    """
    if not str(do_resumo or "").strip() or not str(do_caso or "").strip():
        return []
    a, b = parser(do_resumo), parser(do_caso)
    problemas = []
    if a.get("numero") and b.get("numero") and _so_digitos(a["numero"]) != _so_digitos(b["numero"]):
        problemas.append({"campo": f"{campo}_numero", "resumo": a["numero"], "caso": b["numero"]})
    for parte in ("cidade", "uf"):
        if a.get(parte) and b.get(parte) and _norm(a[parte]).strip() != _norm(b[parte]).strip():
            problemas.append({"campo": f"{campo}_{parte}", "resumo": a[parte], "caso": b[parte]})
    ta, tb = set(_tokens_comparaveis(a.get("rua", ""))), set(_tokens_comparaveis(b.get("rua", "")))
    if ta and tb and not (ta & tb):
        problemas.append({"campo": f"{campo}_rua", "resumo": a.get("rua", ""), "caso": b.get("rua", "")})
    return problemas


def conferir_confirmacao(playbook: Dict[str, Any], telas: List[str], slots: Dict[str, Any],
                         subservice: str, *, parse_address=None) -> Dict[str, Any]:
    """A conferência dos QUATRO campos, antes de qualquer "sim".

    `telas` é uma JANELA — as últimas mensagens da seguradora, da mais antiga
    para a mais nova. São várias porque 📊 na Azul o RESUMO e a PERGUNTA vêm em
    mensagens SEPARADAS: o resumo sozinho não casa `finalize_anchor` nenhuma, e
    a tela que casa ("Como você quer prosseguir?") não tem dado nenhum. Olhar só
    a mensagem atual não conferiria nada justamente ali.

    Devolve `{ok, conferidos, divergencias, resumo, motivo}`.

    **Campo ausente NÃO é divergência.** 📊 O resumo é quase sempre parcial, e
    tratar ausência como erro faria o agente nunca confirmar nada — o oposto da
    decisão do Founder. O preço disso está escrito e é honesto: quando nada é
    comparável o veredito sai `ok` com `motivo="resumo_nao_lido"`, e é esse
    rótulo que vira lista de trabalho de quem mantém o corredor.
    """
    parse_address = parse_address or (lambda s: {})
    resumo: Dict[str, str] = {}
    # DA MAIS NOVA PARA A MAIS ANTIGA — e esta ordem é o conserto de um defeito
    # que anulava a escada de correção inteira.
    #
    # 📊 05/08/2026: com a leitura no sentido natural (mais antiga primeiro) e
    # `setdefault`, o PRIMEIRO valor de cada campo vencia. Sequência real:
    #
    #     URA manda o resumo com 1253   → o guarda reprova, corrigimos
    #     URA manda o resumo com 1235   → o guarda reprovava DE NOVO
    #
    # A janela ainda continha o resumo velho, e ele sombreava o novo. O agente
    # corrigia até estourar o teto e chamava um humano — para um resumo que já
    # estava certo. Um guarda que não sabe reconhecer o conserto que ele mesmo
    # pediu é um guarda que só sabe dizer não.
    #
    # O que se confirma é o que a seguradora disse POR ÚLTIMO. `setdefault`
    # continua sendo o mecanismo (a tela mais nova costuma ser a pergunta, sem
    # dados; a de trás completa o que falta), mas a prioridade inverteu.
    for tela in reversed(list(telas or [])):
        for k, v in ler_resumo(tela).items():
            resumo.setdefault(k, v)

    conferidos: List[str] = []
    divergencias: List[Dict[str, str]] = []
    slots = slots or {}

    # (1) PLACA — mascarada na tela, inteira no caso.
    placa_caso = str(slots.get("veiculo_placa") or "").strip()
    if resumo.get("placa") and placa_caso:
        veredito = bate_com_mascara(resumo["placa"], placa_caso)
        if veredito is not None:  # None = não comparável, e isso não reprova
            conferidos.append("placa")
            if not veredito:
                divergencias.append({"campo": "placa", "resumo": resumo["placa"], "caso": placa_caso})

    # (1b) VEÍCULO — descrição é apelido, e apelido não reprova sozinho.
    # "HILUX SW4" contra "Toyota Hilux SW4 2019" tem interseção; mas a URA também
    # escreve "SW4 4X4 SRV" e o caso "Hilux". Quando a PLACA já foi conferida,
    # ela é a identidade — a descrição vira ruído e só é registrada.
    if resumo.get("veiculo") and str(slots.get("veiculo_descricao") or "").strip():
        ta = set(_tokens_comparaveis(resumo["veiculo"]))
        tb = set(_tokens_comparaveis(str(slots["veiculo_descricao"])))
        if ta and tb:
            conferidos.append("veiculo")
            if not (ta & tb) and "placa" not in conferidos:
                divergencias.append({"campo": "veiculo", "resumo": resumo["veiculo"],
                                     "caso": str(slots["veiculo_descricao"])})

    # (2) SERVIÇO — só reprova quando o resumo nomeia OUTRO serviço conhecido.
    # Texto que não casa nenhuma palavra da tabela ("atendimento") é ilegível,
    # não é divergência.
    canon = canonical_subservice(subservice)
    if resumo.get("servico") and canon:
        texto = _norm(resumo["servico"]).strip()
        do_caso = _PALAVRAS_DE_SERVICO.get(canon)
        outros = [k for k, p in _PALAVRAS_DE_SERVICO.items() if k != canon and re.search(p, texto)]
        if do_caso and re.search(do_caso, texto):
            conferidos.append("servico")
        elif outros:
            conferidos.append("servico")
            divergencias.append({"campo": "servico", "resumo": resumo["servico"], "caso": canon})

    # (3) e (4) ORIGEM e DESTINO.
    if resumo.get("origem") and str(slots.get("local_atual") or "").strip():
        conferidos.append("origem")
        divergencias += _conferir_endereco("origem", resumo["origem"], str(slots["local_atual"]), parse_address)
    if resumo.get("destino"):
        alvo = str(slots.get("local_destino") or "").strip()
        if alvo:
            conferidos.append("destino")
            divergencias += _conferir_endereco("destino", resumo["destino"], alvo, parse_address)
        elif str(slots.get("local_atual") or "").strip():
            # O caso não tem destino (bateria, pneu, chaveiro: o serviço é NO
            # LOCAL). Se o resumo traz destino, ou ele repete a origem, ou a
            # seguradora inventou para onde levar o carro — e um guincho num
            # chamado de bateria é o serviço errado inteiro.
            if _conferir_endereco("destino", resumo["destino"], str(slots["local_atual"]), parse_address):
                conferidos.append("destino")
                divergencias.append({"campo": "destino_inexistente", "resumo": resumo["destino"],
                                     "caso": "(o caso não tem destino)"})

    motivo = ""
    if not conferidos:
        motivo = "resumo_nao_lido" if any(parece_resumo(t) for t in telas or []) else "nada_a_conferir"
    return {"ok": not divergencias, "conferidos": conferidos, "divergencias": divergencias,
            "resumo": resumo, "motivo": motivo}


# ---------------------------------------------------------------------------
# A trava da confirmação única
# ---------------------------------------------------------------------------
#
# 📊 05/08/2026: o MESMO resumo enviado duas vezes → o motor respondeu "1" DUAS
# vezes. `_would_loop` só para na TERCEIRA, e a terceira já é tarde: dois "sim"
# são dois prestadores, dois guinchos e duas cobranças no mesmo chamado.
MAX_CONFIRMACOES = 2
MAX_CORRECOES_POR_CAMPO = 2
MAX_CORRECOES_POR_SESSAO = 3


def digest_da_conferencia(veredito: Dict[str, Any], anchor: str = "") -> str:
    """A identidade do que se está confirmando — a TELA mais os campos LIDOS.

    NÃO é hash da mensagem. A URA reescreve espaço, emoji e negrito entre um
    reenvio e outro, e um digest de bytes acharia que são dois pedidos
    diferentes — que é precisamente o engano que manda o segundo guincho.

    🔴 A âncora entra por um defeito medido em 05/08/2026: sem ela, toda tela
    de confirmação SEM resumo legível colidia num único digest `"vazio"`. Duas
    telas diferentes da mesma família — 📊 na HDI/Yelum, "precisa agora ou
    prefere agendar?" e um "posso confirmar?" adiante — viravam o MESMO pedido,
    e a segunda era recusada como duplicata de uma confirmação que era de outra
    coisa. Com a âncora, tela diferente é pedido diferente; a MESMA tela
    reenviada continua sendo o mesmo pedido, que é o que a trava existe para
    reconhecer.
    """
    itens = sorted((k, _norm(v).strip()) for k, v in (veredito.get("resumo") or {}).items())
    semente = repr((str(anchor or ""), itens))
    return hashlib.sha256(semente.encode("utf-8")).hexdigest()[:16]


def pode_confirmar_de_novo(session: Dict[str, Any], digest: str) -> Dict[str, str]:
    """A segunda confirmação é duplicidade ou etapa nova? `acao` diz o que fazer.

    - primeira vez              -> ok
    - MESMO digest              -> **não confirma**; `acao=perguntar_status`
    - digest diferente          -> etapa nova: confere de novo e confirma
    - teto de MAX_CONFIRMACOES  -> para, com motivo escrito
    """
    ja = list(session.get("confirmacoes") or [])
    if not ja:
        return {"ok": "1", "acao": "", "motivo": ""}
    if any(c.get("digest") == digest for c in ja):
        return {"ok": "", "acao": "perguntar_status", "motivo": "confirmacao_repetida"}
    if len(ja) >= MAX_CONFIRMACOES:
        return {"ok": "", "acao": "", "motivo": "teto_de_confirmacoes"}
    return {"ok": "1", "acao": "", "motivo": ""}


def registrar_confirmacao(session: Dict[str, Any], digest: str, anchor: str, quando: str,
                          *, saida_em: int = 0, tela: str = "") -> None:
    """Grava a confirmação ANTES de emitir.

    ⚠️ A chave é `confirmacoes`, e o nome importa: `snapshot_duravel` corta tudo
    que casa `_CHAVES_PROIBIDAS` (entre elas "token"). Uma trava chamada
    `confirm_token` sumiria do retrato durável e voltaria zerada no restart — e
    uma trava que só mora no Redis não é trava.

    `saida_em` (tamanho do transcript no instante do registro) e `tela` existem
    para uma pergunta só, feita depois: um "sim" REALMENTE saiu? Registrar antes
    de emitir é o certo — a trava tem de valer no instante em que o motor cai —,
    mas registrar não é emitir, e quem confunde as duas coisas bloqueia a
    confirmação legítima da tela seguinte.
    """
    session.setdefault("confirmacoes", []).append(
        {"digest": digest, "anchor": str(anchor or "")[:120], "at": quando,
         "saida_em": int(saida_em), "tela": str(tela or "")[-400:]})


# ---------------------------------------------------------------------------
# Quando o guarda recusa, ele CORRIGE — recusar não é chamar humano
# ---------------------------------------------------------------------------
_OPCAO_DE_CORRECAO = {
    "origem": r"mudar localiza|alterar (?:o )?(?:local|endere)|corrigir endere|alterar dados",
    "destino": r"alterar (?:o )?(?:local de )?destino|mudar destino",
    "placa": r"n[ãa]o,? desejo reiniciar|reiniciar|alterar ve[íi]culo|trocar ve[íi]culo",
    "veiculo": r"n[ãa]o,? desejo reiniciar|reiniciar|alterar ve[íi]culo",
    "servico": r"n[ãa]o,? desejo reiniciar|reiniciar|alterar servi",
}
_ROTULO_DO_CAMPO = {"origem": "endereço de origem", "destino": "destino", "placa": "placa",
                    "veiculo": "veículo", "servico": "serviço"}
_SLOT_DO_CAMPO = {"origem": "local_atual", "destino": "local_destino",
                  "placa": "veiculo_placa", "veiculo": "veiculo_descricao"}


def resposta_de_correcao(divergencias: List[Dict[str, str]], tela: str,
                         slots: Dict[str, Any]) -> Dict[str, str]:
    """A tela OFERECE o conserto? Então o conserto é a resposta.

    A escada, na ordem: (1) a opção da própria tela ("Mudar localização atual",
    "Alterar local de destino"); (2) o valor DO CASO por texto.

    `{"tipo": "opcao"|"texto"|"", "reply": ..., "campo": ...}`. Nunca inventa
    número: o que sai vem dos slots, que já são a única fonte autorizada pelo
    guard de dígitos que existe do outro lado.
    """
    if not divergencias:
        return {"tipo": "", "reply": "", "campo": ""}
    base = str(divergencias[0]["campo"]).split("_")[0]
    padrao = _OPCAO_DE_CORRECAO.get(base)
    if padrao:
        for tecla, rotulo in opcoes_da_tela(tela):
            if re.search(padrao, rotulo, re.IGNORECASE):
                return {"tipo": "opcao", "reply": rotulo if not tecla else tecla, "campo": base}
    fonte = _SLOT_DO_CAMPO.get(base)
    valor = str((slots or {}).get(fonte) or "").strip() if fonte else ""
    if valor:
        return {"tipo": "texto", "campo": base,
                "reply": f"Antes de confirmar: o {_ROTULO_DO_CAMPO.get(base, base)} é {valor}."[:400]}
    return {"tipo": "", "reply": "", "campo": base}


# ===========================================================================
# O QUE A ATENDENTE PRECISA SABER ANTES DE ACIONAR — SPEC-082, 19/08/2026
# ===========================================================================
#
# 🔴 POR QUE ISTO EXISTE.
#
# 📊 Medido em 19/08/2026: o `agent_system_prompt` da atendente da Resulta tem
# 1.539 caracteres e é bom em segurança — mas não contém as palavras
# "eletrodoméstico" nem "máquina de lavar", nem diz o que coletar, nem que
# conserto de eletrodoméstico é AGENDADO. O mesmo vale para os outros seis
# agentes cadastrados.
#
# O conhecimento existia — espalhado entre a descrição dos parâmetros da
# ferramenta, comentários de código e as telas mapeadas — e não chegava à
# conversa. A atendente descobria o que faltava só DEPOIS de chamar a
# ferramenta e receber `missing_data`, o que na frente do cliente parece
# hesitação.
#
# 🔴 E POR QUE ELE É GERADO, E NÃO ESCRITO À MÃO (CLAUDE.md §5).
#
# Um texto fixo seria uma SEGUNDA fonte de verdade sobre o que cada rota
# exige. No dia em que um `required_slots` mudasse, o prompt continuaria
# ensinando a versão antiga — e ninguém veria, porque prompt não tem teste de
# compilação. Aqui tudo sai do próprio playbook: mudou o corredor, mudou o que
# a atendente sabe, no mesmo commit.
#
# Foi exatamente esse o defeito de 18/08: `aparelho_marca_modelo` virou dois
# campos e o resto do produto não soube.

#: Como cada slot é dito para uma pessoa. Chave interna nunca vai para a tela
#: de quem trabalha — a lição do dossiê que escrevia `assistencia.residencial.
#: encanador` para um humano ler no WhatsApp.
_COMO_PERGUNTAR = {
    "titular_cpf": "o CPF do titular da apólice",
    "titular_nome": "o nome do titular",
    "endereco_numero": "o número da residência",
    "telefone_contato": "o telefone de quem vai receber o prestador no local",
    "pessoa_no_local": "quem estará no local para receber o prestador",
    "problema_descricao": "o que está acontecendo (com as palavras do cliente)",
    "periodo_preferido": "o período preferido — manhã (9h-13h) ou tarde (13h-18h)",
    "aparelho_marca": "a marca do aparelho (Brastemp, Electrolux, Consul...)",
    "aparelho_modelo": "o modelo ou uma descrição do aparelho — aproximado serve",
    "aparelho_idade": "há quantos anos o aparelho foi fabricado",
    "risco_confirmado_sem_fumaca": "se NÃO há fumaça, faísca ou cheiro de queimado",
    "risco_confirmado_registro_fechado": "se o registro de água já foi fechado",
    "vazamento_local": "onde é o vazamento",
    "agua_escorrendo": "se a água ainda está escorrendo",
    "veiculo_placa": "a placa do veículo",
    "local_atual": "onde o veículo está agora",
    "local_destino": "para onde o veículo deve ser levado",
    "quando": "se precisa agora ou prefere agendar",
    "titular_nascimento": "a data de nascimento do titular (a Mapfre confere a identidade com ela)",
    "aparelho_marca_modelo": "a marca e o modelo do aparelho",
    "ponto_referencia": "um ponto de referencia proximo",
    "servico_texto": "qual servico o cliente precisa, em uma frase",
}

#: Slots que o MOTOR preenche sozinho. Pedi-los ao cliente seria perguntar o
#: número de uma tecla de menu que ele nunca viu.
_NAO_SE_PERGUNTA = {
    "tipo_servico_opcao", "servico_opcao", "telefone_adicionar_opcao",
    "problema_eletrico_opcao", "data_agendamento_opcao",
    "periodo_agendamento_opcao", "eletrodomestico_opcao",
    "eletrodomestico_categoria_opcao", "profissional_opcao", "veiculo_opcao",
    "dados_confirmados",
}


def conhecimento_de_assistencia(playbook_refs: Sequence[str]) -> str:
    """O bloco que ensina a atendente a conduzir um acionamento.

    Recebe os corredores que ESTA corretora pode usar e devolve texto para o
    prompt. Corretora sem corredor recebe string vazia — e um agente que não
    pode acionar não deve ler instruções sobre acionar.
    """
    refs = [r for r in (playbook_refs or []) if get_playbook(r)]
    if not refs:
        return ""

    linhas: List[str] = [
        "=== ASSISTÊNCIA 24H: COMO CONDUZIR UM ACIONAMENTO ===",
        "",
        "Você tem a ferramenta `insurer_dispatch`. Ela fala com o WhatsApp da "
        "seguradora no seu lugar, do início até o protocolo. Ela só trabalha "
        "com o levantamento COMPLETO — por isso colete tudo antes de chamá-la, "
        "uma pergunta por vez, com as palavras do cliente.",
        "",
        "O QUE COLETAR, por tipo de pedido:",
    ]

    # 🔴 AGRUPADO POR ROTA, NÃO POR SEGURADORA.
    #
    # 📊 Uma linha por (corredor × rota) dava 7.763 caracteres para os 14
    # corredores — cinco vezes o prompt inteiro da atendente, repetindo "peça
    # o CPF" catorze vezes. Prompt que enterra a instrução importante debaixo
    # de repetição não ensina: dilui.
    #
    # E é como uma pessoa pensa: "para máquina de lavar eu pergunto X" vale
    # para qualquer seguradora. O que varia entre elas são as TECLAS da URA, e
    # dessas quem cuida é o corredor — a atendente nunca as vê.
    #
    # A união dos slots é deliberada: se UMA seguradora exige o período, é
    # melhor a atendente perguntar sempre do que descobrir que faltou depois
    # de já ter dito ao cliente que ia acionar.
    por_rota: Dict[str, Dict[str, Any]] = {}
    for ref in refs:
        pb = get_playbook(ref) or {}
        rotulos = pb.get("subservice_labels") or {}
        seguradora = str(pb.get("insurer_key") or "").upper()
        for rota, sub in sorted((pb.get("subservices") or {}).items()):
            pedir = [s for s in (sub.get("required_slots") or [])
                     if s not in _NAO_SE_PERGUNTA]
            if not pedir:
                continue
            reg = por_rota.setdefault(
                rota, {"nome": str(rotulos.get(rota) or rota).replace("_", " "),
                       "slots": [], "cias": []})
            for s in pedir:
                if s not in reg["slots"]:
                    reg["slots"].append(s)
            if seguradora and seguradora not in reg["cias"]:
                reg["cias"].append(seguradora)

    for rota in sorted(por_rota):
        reg = por_rota[rota]
        itens = "; ".join(_COMO_PERGUNTAR.get(s, s.replace("_", " "))
                          for s in reg["slots"])
        linhas.append(f"  · {reg['nome']}: {itens}")

    # O que muda a EXPECTATIVA do cliente. Dito depois, vira reclamação.
    # 🔴 AGRUPAR PRIMEIRO, DEDUPLICAR DEPOIS.
    #
    # A primeira versão fazia o contrário: descartava o par cujo TEXTO já
    # tinha aparecido, e só então agrupava. Como os quatro emergenciais
    # compartilham a mesma frase, sobrava um só — o primeiro em ordem
    # alfabética. 📊 O bloco gerado dizia "chaveiro — vai HOJE" e ficava
    # calado sobre eletricista, encanador e desentupimento; e dizia
    # "eletrodomesticos — é agendado" sem citar a máquina de lavar, que é
    # justamente a rota do teste de hoje.
    #
    # Uma rota que some da lista não vira erro: vira silêncio, que é pior.
    agrupado: Dict[str, List[str]] = {}
    for ref in refs:
        pb = get_playbook(ref) or {}
        for rota, texto in sorted((pb.get("expectativa_do_desfecho") or {}).items()):
            nomes = agrupado.setdefault(str(texto), [])
            legivel = rota.replace("_", " ")
            if legivel not in nomes:
                nomes.append(legivel)
    if agrupado:
        linhas += ["", "O QUE ACONTECE DEPOIS (avise o cliente ANTES de acionar):"]
        for texto, rotas in sorted(agrupado.items(), key=lambda kv: kv[1]):
            linhas.append(f"  · {', '.join(sorted(rotas))} — {texto}")

    # As regras que a seguradora declara na própria tela.
    regras = []
    for ref in refs:
        pb = get_playbook(ref) or {}
        for _rota, lista in sorted((pb.get("regras_para_o_cliente") or {}).items()):
            for r in lista or []:
                if r not in regras:
                    regras.append(r)
    if regras:
        linhas += ["", "REGRAS DA SEGURADORA que o cliente precisa ouvir ANTES "
                       "(elas podem fazer o chamado ser recusado no local):"]
        linhas += [f"  · {r}" for r in regras]

    # O que o cliente tem de saber para receber o prestador.
    # 🔴 DUAS PENEIRAS, e as duas foram medidas na primeira geracao do bloco.
    #
    # (a) 📊 no comeco da linha marca OBSERVACAO INTERNA (CLAUDE.md §12.1), e
    #     duas delas vazaram inteiras para o texto que a atendente falaria com
    #     o cliente -- com o proprio emoji de medicao no meio da frase.
    # (b) "maior de 18 anos no local" aparecia TRES vezes, em tres redacoes,
    #     porque tres corredores dizem a mesma coisa com palavras diferentes.
    #     Repeticao em prompt nao reforca: ocupa espaco e ensina que a lista
    #     pode ser lida na diagonal.
    instrucoes: List[str] = []
    assinaturas: set = set()
    _por_assinatura: Dict[Any, str] = {}
    for ref in refs:
        pb = get_playbook(ref) or {}
        for i in pb.get("client_instructions") or []:
            texto = str(i).strip()
            if not texto or texto.startswith("📊"):
                continue
            # assinatura = as palavras que carregam o sentido, sem a redacao
            assinatura = frozenset(
                w for w in _norm(texto).split()
                if len(w) > 3 and w not in ("para", "pelo", "pela", "esta",
                                            "sera", "deve", "necessario",
                                            "precisa", "sobre", "and"))
            if assinatura in assinaturas:
                continue
            # sobreposicao alta com algo que ja entrou = mesma regra
            #
            # 🔴 E quando colidem, fica a redacao GENERICA. A primeira versao
            # ficava com a primeira que chegasse, e o que sobrou foi "maior de
            # 18 anos no local para acompanhar o GUINCHO" — dito a um cliente
            # de maquina de lavar. A regra vale para os dois; a palavra
            # "guincho" so vale para um. Frase que cita o servico errado faz o
            # cliente achar que a atendente se perdeu.
            _ESPECIFICAS = ("guincho", "reboque", "veiculo", "chaves", "carro")
            colidiu = next(
                (a for a in assinaturas
                 if len(assinatura & a) >= max(3, int(len(assinatura) * 0.6))),
                None)
            if colidiu is not None:
                nova_e_generica = not any(p in _norm(texto) for p in _ESPECIFICAS)
                velha = _por_assinatura.get(colidiu, "")
                velha_e_generica = not any(p in _norm(velha) for p in _ESPECIFICAS)
                if nova_e_generica and not velha_e_generica:
                    instrucoes[instrucoes.index(velha)] = texto
                    _por_assinatura[colidiu] = texto
                continue
            assinaturas.add(assinatura)
            _por_assinatura[assinatura] = texto
            instrucoes.append(texto)
    if instrucoes:
        linhas += ["", "AVISE TAMBÉM, ao confirmar o acionamento:"]
        linhas += [f"  · {i}" for i in instrucoes]

    linhas += [
        "",
        "COMO TERMINA:",
        "  · A ferramenta devolve o RESULTADO. Se vier um protocolo, passe-o ao "
        "cliente junto do dia e do período combinados.",
        "  · Se o retorno indicar simulação, teste ou pendência, NÃO diga que "
        "acionou. Diga o que de fato aconteceu.",
        "  · Nunca invente protocolo, prazo ou nome de prestador.",
        "  · Se faltar um dado, a ferramenta diz qual. Pergunte ao cliente e "
        "chame de novo — não desista do caso nem improvise o dado.",
    ]
    return "\n".join(linhas)

# 🔴 P-084-8 — a porto passa a entregar o QUANDO, não só o protocolo.
PORTO_AUTO_WHATSAPP_V1["capture_anchors"] = {
    **PORTO_AUTO_WHATSAPP_V1["capture_anchors"],
    "schedule_porto": _ANCORA_DE_AGENDAMENTO_PORTO,
}

# 🔴 P-084-8 — a porto passa a entregar o QUANDO, não só o protocolo.
PORTO_RESIDENCIAL_WHATSAPP_V1["capture_anchors"] = {
    **PORTO_RESIDENCIAL_WHATSAPP_V1["capture_anchors"],
    "schedule_porto": _ANCORA_DE_AGENDAMENTO_PORTO,
}
