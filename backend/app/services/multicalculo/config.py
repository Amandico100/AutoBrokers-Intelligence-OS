# -*- coding: utf-8 -*-
"""A configuração COMERCIAL do multicálculo — SPEC-130-A U2 (D-MC-62…72, D-130A-04/05) · SPEC-130-A.1 (D-130A1-*).

🔴 Este é o ÚNICO lugar com os números comerciais (comissão, alvo, validade, lembretes, pesos da nota, quantas
opções). O Founder (06/10): *"ajustes futuros virão dos comerciais: deixe tudo como CONFIGURAÇÃO, nunca constante
espalhada"*. O guarda `tests/test_spec130a_a_config.py::test_g8_nenhum_numero_comercial_fora_da_config` procura
estes números nos outros arquivos da 130-A e fica VERMELHO se um deles aparecer lá.

`PADRAO_DO_PRODUTO` vale para toda corretora que não configurou o seu; `carregar(company_id, db=)` devolve o padrão
⊕ a linha da corretora em `multicalculo_config` (migration 20261006_01). Só as chaves que o padrão conhece entram;
um valor de tipo errado ou uma régua incoerente (piso acima do autônomo, pesos que não somam 100) é IGNORADO com
log — vale o padrão daquela seção, nunca um número quebrado.
"""
from __future__ import annotations

import copy
import logging
import re
import unicodedata
from typing import Any, Dict, Iterable, Mapping, Optional

logger = logging.getLogger(__name__)

TABELA = "multicalculo_config"

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class ConfigIndisponivel(RuntimeError):
    """O banco não respondeu: a config da corretora pode ter um piso MAIOR que o padrão — nunca se adivinha."""


#: 📊 = declarado pelas comerciais (n = 4, ESTRATEGIA §1) ou decidido pelo Founder · 💭 = valor inicial a calibrar
PADRAO_DO_PRODUTO: Dict[str, Any] = {
    # D-MC-66/67/68/64 — a margem. % de comissão da corretora.
    # 🔴 D-MC-68 CORRIGIDA (Founder 06/10, 23h: "EU NÃO FALEI ISSO"): o agente desce até o PISO SOZINHO, sem aprovação
    # humana, mas PASSO A PASSO (`passo_pp`), nunca direto. De `entrada` até `autonomo_minimo` ele negocia; o trecho
    # `autonomo_minimo` → `piso` (≈ 2 pp) é a ALAVANCA DE FECHAMENTO: guardada para o fim, oferecida em R$ (nunca em %)
    # como a condição que a seguradora devolveu no recálculo, e só com o cliente fechando.
    "comissao": {
        "entrada": 15.0,          # 📊 cliente novo: 15 % (as 4 comerciais, §1.2/§1.3)
        "autonomo_minimo": 12.0,  # 📊 D-MC-68: até 12 % é a negociação normal, passo a passo
        "piso": 10.0,             # 📊 D-MC-64/68: o piso de todas; o agente chega aqui SOZINHO, só como fechamento
        "passo_pp": 1.0,          # 💭 de quanto em quanto a comissão desce (o Founder: "aos poucos, não direto")
        # SPEC-129-C D-129C-05 — a comissão de RE vai EXPLÍCITA no item do cálculo (📊 B0-a 11/10: na conta da
        # corretora o Agger traz percComissaoEmpres = 0 nas 10 seguradoras do empresarial; Cond/Resid = 10). Por
        # ramo (chave = o código do ramo como texto); None = a `entrada` acima (o padrão do produto, igual ao auto).
        "por_ramo": {"16": None, "2": None, "18": None},
        # Red P4 (conserto 129-C) — o TETO da comissão explícita do item (o pedido, a config por ramo, o ajuste de RE):
        # acima disso é erro de digitação (o red passou 500 %), nunca uma comissão. 💭 50 = valor inicial a calibrar
        # (nenhuma das comerciais citou comissão acima de 30 %). Piso: > 0 (o 0 escrito é o que a D-129C-05 evita).
        "teto_pct": 50.0,
    },
    # D-MC-66 — novo COM apólice: mirar 💭 ~10–15 % abaixo do preço atual quando der, guardando margem
    "alvo_abaixo_da_atual_pct": {"minimo": 10.0, "maximo": 15.0},
    # D-MC-66 — renovação: tenta +1–2 pp de comissão sobre a do ano anterior. SPEC-131-A (D-131-01): a renovação é
    # CALCULADA quando vence em ≤ 10 dias (era ~15, D-MC-66). Um número só: o madrugada lê o mesmo em
    # `servicos.renovacao.antecedencia_dias` (espelho resolvido em `mesclar`, `_resolver_renovacao`)
    "renovacao": {"antecedencia_dias": 10, "comissao_a_mais_pp": {"minimo": 1.0, "maximo": 2.0},
                  # SPEC-129-C D-129C-06 — o reajuste da cobertura BÁSICA (incêndio) na renovação de RE, por ramo, em %.
                  # Padrão 15 = a palavra do Founder (10/10). 📊 AGREGADO-POR-RAMO §3 (B0-c, 11/10, 41 pares de
                  # condomínio, mesmo cliente a 300–430 dias): o mais COMUM é +10 % (16 de 41; +15 % em 6; mediana
                  # +13,3 %); empresarial 4 de 4 no mesmo endereço = +10 %; residencial inconclusivo (2 pares).
                  # 🧑 o Founder confirma o número — a corretora troca o dela aqui.
                  "reajuste_basica_pct": {"16": 15.0, "2": 15.0, "18": 15.0}},
    # D-MC-71 / D-130A-05 — validade = hoje + a MENOR validade das seguradoras do quadro. 📊 padrão 5 = o menor
    # medido (n = 4). `por_seguradora`: nome da seguradora (como o Agger devolve) → dias. Vazio até medir.
    "validade": {"padrao_dias": 5, "por_seguradora": {}},
    # U7 — o link da página vive a validade da proposta + esta folga 💭
    "link": {"folga_dias": 2},
    # D-MC-71 — 1 lembrete ~24 h depois, em horário comercial, + 1 antes de vencer a validade
    "lembretes": {"primeiro_apos_h": 24, "antes_de_vencer_h": 24, "horario_comercial": {"inicio_h": 9, "fim_h": 18}},
    # U1 — a NOTA 0–100 da opção: pesos 💭 (somam 100)
    "nota": {"pesos": {"preco": 60, "franquia": 25, "coberturas": 15}},
    # D-MC-74 / D-MC-69 / D-130A-09 — quantas opções: 2 no WhatsApp, 3 no carrossel da página
    "opcoes": {"no_whatsapp": 2, "na_pagina": 3},
    # qual CÁLCULO (a opção da porta) alimenta cada papel da proposta. `completa_mais` entra numa fatia própria
    # (o preset e a constraint): sem cálculo dela, a 3ª opção é "Outra completa" (D-130A-09)
    "calculo_por_papel": {"completa": "padrao", "economica": "economica", "completa_mais": "completa_mais",
                          # SPEC-130-A.1 — o "mínimo do mínimo" (D-130A1-05): só o canal pede; mostra a MAIOR economia
                          # possível, sempre com o que deixa de cobrir. Nunca é a recomendada.
                          "minima": "minima"},
    # D-130A-04 — vencedora entre corretoras = a menor completa; empate: estes critérios, nesta ordem
    "desempate_entre_corretoras": ["nota_google", "ordem_de_adesao"],
    # D-MC-63/67 — 📊 128 E5: estas seguradoras OBEDECEM o desconto e IGNORAM a comissão (o botão da margem nelas é
    # o desconto). Casamento pelo nome normalizado (sem acento, minúsculo), começo da palavra.
    "seguradoras_que_obedecem_desconto": ["porto", "azul", "itau"],
    # D-MC-67 ① — o desconto que cada seguradora LIBERA no Agger (`percDesconto`), por nome → %. 📊 não medido:
    # vazio = o passo ① não roda nas que obedecem comissão (a corretora configura quando souber)
    "desconto_permitido_pct": {},
    # D-MC-67 — a ordem do "mais barato" (margem ANTES de cobertura) e o nível de cada corte (rótulos MEDIDOS de
    # `presets.VALORES_DO_AJUSTE`)
    "ordem_do_mais_barato": ["desconto", "comissao", "franquia", "carro_reserva", "vidros", "assistencia"],
    "cortes_de_cobertura": {"franquia": "normal", "carro_reserva": "7 dias", "vidros": "basico",
                            "assistencia": "basica"},
    # D-MC-72 — a cotação-alvo: quantas seguradoras e tentativas por etapa (cada tentativa = 1 recálculo da
    # corretora inteira, ~30–50 s 📊 E7); quais cortes o motor ainda RECOMENDA (com 1 corte só) 💭
    "negociacao": {"max_seguradoras": 3, "max_tentativas_por_etapa": 6,
                   "cortes_recomendaveis": ["franquia", "carro_reserva"]},
    # P-129B-06 / D-130A-03 — produtos de ASSINATURA: o `premio_total` não é prêmio anual e o `premio_mensal` é
    # derivado (premio_total/12) → classe DIFERENTE, preço nunca exibido. Casa por seguradora (igual) ou produto
    # (contém), nomes normalizados.
    "produtos_de_assinatura": [{"seguradora": "Azul Assinatura"}, {"seguradora": "Azul por Assinatura"},
                               {"produto": "assinatura"}],
    # SPEC-129-C D-129C-07 — a PREFERÊNCIA de seguradoras, por ramo, por corretora: lista ORDENADA (o nome como o
    # Agger devolve — casamento por começo de palavra, `casa_seguradora` — ou o código da seguradora no Agger, int).
    # Vazia = nenhuma preferida: todas as do ramo na conta são cotadas e comparadas igual. A comparação MARCA a
    # preferida no ranking (e desempata por ela no mesmo prêmio); NUNCA esconde as outras.
    "preferencias_de_seguradoras": {"31": [], "16": [], "2": [], "18": []},
    # SPEC-129-C — o que torna duas ofertas de RE COMPARÁVEIS além da MESMA básica: estas coberturas, quando a
    # maioria do quadro as devolve, têm de estar na oferta com o mesmo valor ou mais. Chaves do Agger
    # (`cotacao.configuracoes`, fixtures `formulario_*`). Critério da lista: presentes em ≥ 12 dos 15 negócios lidos
    # por ramo (📊 AGREGADO-POR-RAMO §2, B0-c 11/10) — condomínio: elétricos, impacto, vidros, RC condomínio, RC
    # síndico, vendaval, portões (15/15), danos morais (14), tumulto e roubo (13) · residencial: elétricos e
    # vendaval (13), RC familiar (12) · empresarial: elétricos (15), RC (12). A básica é sempre exigida (à parte).
    "coberturas_essenciais": {
        "16": ["isDanosEletricos", "isDanosImpactoVeiculo", "vidros", "isValorCondominio", "isValorSindico",
               "isDanosVendaval", "isDanosPortoes", "isDanosMorais", "tumultoGreveLockOut", "isDanosRoubo"],
        "2": ["isDanosEletricos", "isDanosVendaval", "responsabilidadeCivil"],
        "18": ["isDanosEletricos", "responsabilidadeCivil"],
    },
    # textos da página que a corretora pode trocar (None = o padrão de `manual_de_negociacao`)
    "faq": None,
    "sinistro": None,
    # U4 — prova social: a ficha do Google SÓ quando a corretora a CONFIRMOU (📊 06/10 a busca por nome achou
    # outra empresa para uma das corretoras). {"nota", "avaliacoes", "data", "fonte"} ou None
    "google_confirmado": None,
    # D-MC-55 — o nome do CANAL comparador (marca do PRODUTO, não de corretora). É configuração, não constante da
    # página: a proposta do canal leva `canal.nome` no modelo (laudo do red team, 06/10: RT-10)
    # SPEC-130-A.1 — o canal comparador ao consumidor (marca própria, D-130A1-01): a mensagem pós-cálculo e o follow-up.
    "canal": {
        "nome": "Quem Cobra Menos",
        # 🔴 "Corretora Nível 5" é o selo do PROGRAMA (D-130A1-04): toda corretora que entra no canal cumpre a lista dele;
        # não é medida de porte. A corretora pode desligar o selo na própria config (ex.: enquanto não cumpre a lista).
        "selo": {"nome": "Corretora Nível 5", "ligado": True},
        # quantas seguradoras a mensagem lista em "Melhor preço por seguradora" (o resto está no link)
        "lista_por_seguradora": 6,
        # D-130A1-14 — o tempo da mensagem só aparece até este teto 💭 (acima, some; nunca um tempo menor que o medido).
        # 📊 canário 07/10: último preço aos 495 s (fila do robô + corretoras em série, portal-worker com concorrência 1).
        # SPEC-133-A F0 (Founder 07/10): o teto padrão sobe para 180 s ("em 1,5 minutos" cabe; "8 min" não)
        "tempo_exibido_ate_s": 180,
        # SPEC-133-A F0 (ordem do Founder 07/10 — TESTE CONTROLADO e temporário com o círculo social dele, para medir
        # conversão): "Fiz N Cotações" = `base` + os preços que voltaram nas opções + as tentativas sem preço (erro,
        # recusa, sem resposta) das opções. A base vem SÓ daqui 💭; desligar = `base: 0` (só o real). O real é contado
        # à parte no modelo (`resumo.volume_do_canal`), para a base nunca se confundir com o que aconteceu.
        "volume": {"base": 100},
        # D-130A1-06 — termina com UMA pergunta; sem resposta, até 2 lembretes, nunca mais que isso 💭
        "follow_up": {"primeiro_apos_min": 15, "segundo_apos_h": 24, "max_sem_resposta": 2,
                      "horario_comercial": {"inicio_h": 9, "fim_h": 20}},
        # SPEC-133-A (F1, costura) — o piloto fechado: quantas cotações um número convidado faz por dia 💭 (o convidado
        # pode ter `limite_dia` próprio, que vence) e o teto anti-laço de mensagens NOSSAS por conversa por dia 💭 (a
        # conversa inteira cabe em ~15: consentimento + ~12 perguntas + resultado + pergunta final + 2 lembretes;
        # resultado e lembretes contam).
        "limite_cotacoes_por_dia": 3,
        "teto_mensagens_por_dia": 60,
        # SPEC-133-A (conserto B2) — quanto tempo a pessoa pode ficar em "calculando" com o run vivo 💭: passou disso
        # sem resultado, a conversa SAI (etapa `falhou`, as respostas somem, UMA frase honesta). O run do canal tem
        # teto de acompanhamento de 11 min (`canal/workflows.TETO_DO_ACOMPANHAMENTO_S`) + publicar e mandar.
        "tempo_max_calculando_min": 20,
        # SPEC-133-A (conserto 7) — a conversa parada há mais que isto 💭 tem as respostas apagadas no próximo acesso
        # (o registro do consentimento, append-only em `canal_consentimentos`, fica).
        "retencao_conversa_dias": 30,
        # SPEC-133-A.1 F2 (D-133A1-02, Founder 10/10) — a conversa só PULA "homem ou mulher?" quando o primeiro nome é
        # deste lado em pelo menos esta % das pessoas com o nome no Censo 2010 do IBGE 💭 ("70 % homem, podemos
        # concluir; 60/40 talvez seja ideal perguntar"). Vale de 50 (exclusive) a 100; fora disso, este padrão.
        "sexo_pelo_nome_min_pct": 70,
        # SPEC-133-A (costura) — a RESERVA do número da conversa do canal (o "Quero fechar" da página volta para ele).
        # O primeiro é SEMPRE o da integração ativa do canal (`canal.envio.numero_do_canal`); vazio = sem reserva.
        "whatsapp": "",
    },
    # SPEC-131-0 parte A · F4 (D-131-0-07/08/10/12) — o MANUAL DE CADA SERVIÇO. O Founder (10/10): *"o manual de regras
    # para renovação, como pensar, como cotar, deve ser diferente de Quem Cobra Menos e da cotação… se eu falar que é
    # para todas a mesma regra, aí ajusta em tudo"*. Tudo acima é a BASE da corretora (vale para os três); cada serviço
    # pode SOBREPOR qualquer chave da base na linha da corretora (`servicos.<serviço>.<chave da base>`) — e o que um
    # serviço sobrepõe nunca vaza para outro (`carregar(…, servico=)`).
    # `modo` — *"a corretora deve poder escolher se quer que o agente faça só o cálculo… ou ligar a negociação"*:
    #   calcular (deixa pronto no Agger) · calcular_entregar (manda ao cliente) · calcular_entregar_negociar.
    # `excecoes_do_modo` — [{ramo?, valor_acima_de?, modo}]: quando a condição casa, vale o modo da exceção; se várias
    #   casam, vale a MAIS CONTIDA (nunca uma exceção liga mais do que outra deixou).
    "servicos": {
        # o Quem Cobra Menos É calcular, entregar e negociar — é a natureza do canal
        "qcm": {"modo": "calcular_entregar_negociar", "excecoes_do_modo": []},
        # 💭 Cotação e Renovação nascem no modo mais contido: a corretora liga a entrega/negociação quando quiser
        "cotacao": {"modo": "calcular", "excecoes_do_modo": [],
                    # SPEC-132-B (D-132B-06) — os CÁLCULOS da cotação, na ordem do disparo (1 a 3, sem repetir, a
                    # `padrao` sempre — é dela que sai a Recomendada). As 3 da página de venda: Recomendada (padrao),
                    # Mais em conta (economica) e Mais completa (completa_mais). ⛔ a `minima` é só do canal.
                    "opcoes": ["padrao", "economica", "completa_mais"],
                    # SPEC-132-B (D-132B-01/02) — os TEXTOS da página de VENDA (`proposta_cotacao_html`). Padrão do
                    # produto, verdadeiros para QUALQUER corretora; a corretora troca cada lista inteira na linha dela
                    # (`servicos.cotacao.pagina.<chave>`). `{corretora}` e `{validade}` são trocados na página pelo
                    # nome e pela data REAIS. ⛔ nenhum texto promete WhatsApp, valor de devolução ou prazo da
                    # seguradora; `diferenciais` nasce VAZIO (bloco sem dado some — nunca um diferencial inventado).
                    "pagina": {
                        "diferenciais": [],
                        "depois_do_sim": [
                            "Você escolhe a opção e fala com a gente. Tiramos as últimas dúvidas e conferimos os seus "
                            "dados.",
                            "Fazemos a proposta na seguradora. Se ela pedir vistoria do carro, avisamos e combinamos "
                            "com você.",
                            "A apólice chega no seu e-mail. E a {corretora} continua do seu lado durante todo o "
                            "seguro.",
                        ],
                        "faq": [
                            {"pergunta": "Por que fechar com uma corretora?",
                             "resposta": "Porque a corretora trabalha para você, não para a seguradora: compara várias "
                                         "de uma vez, explica o que cada cobertura faz e representa você diante da "
                                         "seguradora — na contratação e, principalmente, se precisar acionar o "
                                         "seguro."},
                            {"pergunta": "E se eu bater o carro?",
                             "resposta": "Você avisa a {corretora}. A gente orienta o que fazer, abre o aviso na "
                                         "seguradora com você e acompanha até o fim. A franquia de cada opção é a sua "
                                         "parte no conserto, quando houver."},
                            {"pergunta": "O preço pode mudar?",
                             "resposta": "Os preços desta cotação valem até {validade}. Depois disso a seguradora pode "
                                         "recalcular, e a gente atualiza a cotação para você, sem custo."},
                            {"pergunta": "Como eu pago?",
                             "resposta": "À vista ou parcelado, nas formas que cada seguradora aceita (cartão de "
                                         "crédito, boleto ou débito em conta). Os cartões mostram a parcela de cada "
                                         "opção."},
                            {"pergunta": "Posso cancelar depois?",
                             "resposta": "Pode. A devolução do que você já pagou segue as regras da seguradora para o "
                                         "período que ficou sem uso, e a gente cuida do pedido com você."},
                            {"pergunta": "Preciso fazer vistoria?",
                             "resposta": "Depende da seguradora e do carro. Se ela pedir, avisamos antes e combinamos "
                                         "o melhor horário com você."},
                            {"pergunta": "Os meus dados estão seguros?",
                             "resposta": "Estão. Usamos os seus dados só para cotar e contratar o seu seguro, como manda "
                                         "a Lei Geral de Proteção de Dados (LGPD). Esta página não mostra o seu CPF nem "
                                         "o seu telefone."},
                        ],
                    }},
        "renovacao": {"modo": "calcular", "excecoes_do_modo": [],
                      # D-131-0-05 / §5 F3 — o Agger do comercial falhou (senha recusada): a conta da CORRETORA só
                      # assume quando a apólice vence em MENOS que isto, em dias 💭 (lido por `qual_agger.decidir`)
                      "conta_global_se_vence_em_dias": 5,
                      # SPEC-131-B (D-131-04, Founder) — "Com qual conta": `responsavel` = o Agger de quem cuida da
                      # apólice (as regras da 131-0 A) · `corretora` = SEMPRE o Agger da corretora, por escolha dela
                      # (regra própria, sem aviso de desvio). Lido por `qual_agger.decidir` (`conta_da_renovacao`)
                      "conta": "responsavel",
                      # SPEC-131-A §4/§5 — A MADRUGADA DA RENOVAÇÃO (lidas pela F1 `madrugada.py` e pela F3 `motor.py`)
                      # D-131-01: calcula o que vence em ≤ isto (1–60 dias). Espelho de `renovacao.antecedencia_dias`
                      # (a tela grava lá): `mesclar` resolve UM número e escreve nos dois lugares.
                      "antecedencia_dias": 10,
                      # §4 — no FUSO da corretora, 7 dias por semana (HH:MM). Prosseguir sobre sessão aberta só entre
                      # `prosseguir_de` e `prosseguir_ate`; a pessoa voltou → nova tentativa a cada `retentativa_min`
                      # (D-131-29, Founder 12/10: de hora em hora)
                      # SPEC-132 (Founder 14/10: "às 7h tudo cotado; a hora que começa não interessa"): calcular
                      # 02:00 → 01:00 (espera a lista terminar) · `ultimo_inicio` (novo): depois dele NENHUM cálculo
                      # começa · conferir 05:30 → 06:05. A conta da janela está em `madrugada.py`
                      "janela": {"preparar": "00:30", "calcular": "01:00", "ultimo_inicio": "05:55",
                                 "conferir": "06:05", "desvio": "06:15", "avisar": "06:45", "prosseguir_de": "01:00",
                                 "prosseguir_ate": "06:30", "retentativa_min": 60},
                      # §4 — 1 a 3, na ordem do disparo; só `presets.OPCOES_DA_RENOVACAO`. ⛔ econômica e mínima
                      # NUNCA numa renovação (mutação 7): a validação recusa e volta a este padrão
                      "opcoes": ["anterior", "franquia_reduzida", "completa_mais"],
                      # D-131-30 — sessões do Agger ao mesmo tempo POR CORRETORA (o do processo é o env
                      # MULTICALCULO_TETO_SESSOES); 1 até o BLOCO 0 A4 medir 2 logins da mesma corretora juntos
                      "teto_sessoes_corretora": 1,
                      # D-131-03 / T-156 — o ACEITE do "Prosseguir" da madrugada, POR CONTA: ids da conta do Agger
                      # (`portal_accounts.id`) ou da dona (`user_id`). Vazio = a política fica DESLIGADA em todas.
                      # Lida CRUA pelo motor (F3, `_cfg_madrugada`); registrada aqui para a leitura validar e para a
                      # tela "Serviços" (que só regrava as chaves que edita) nunca apagá-la — costura F4
                      "prosseguir_aceites": [],
                      # SPEC-132 (Founder 14/10, revê a D-131-33 que fixava 12): SEM teto — null = o RELÓGIO decide
                      # (`janela.ultimo_inicio`); o que não começou fica para a próxima noite, na frente. A corretora
                      # pode pôr um teto por conta do Agger por noite, NUNCA abaixo de 30 (30–500). A antecipação (0–20
                      # dias 💭) puxa o que vence nos próximos dias quando sobra relógio (lidos pela F1)
                      "teto_por_conta_noite": None,
                      "antecipar_ate_dias": 7,
                      # D-131-16 (BLOCO 0 A5 📊 `per_c` > 0 em 20/20 nas duas corretoras, é a comissão da CORRETORA):
                      # a opção `anterior` leva a comissão do ano anterior + isto, em pontos percentuais (0–5) 💭
                      "comissao_a_mais_pp": 1.0},
    },
}

#: os serviços que têm manual próprio (D-131-0-32: a mesma lista da coluna `multicalculo_pedidos.servico`)
SERVICOS = ("qcm", "cotacao", "renovacao")
#: do mais contido ao mais aberto — a ORDEM importa (`modo_do_servico` escolhe o mais contido entre exceções)
MODOS = ("calcular", "calcular_entregar", "calcular_entregar_negociar")
#: as chaves PRÓPRIAS de cada serviço (o resto do bloco do serviço sobrepõe a base)
_CHAVES_PROPRIAS = {s: frozenset(PADRAO_DO_PRODUTO["servicos"][s]) for s in SERVICOS}


# ---------------------------------------------------------------------------------------------------------------------
def normalizar(texto: Any) -> str:
    """Sem acento, minúsculo, espaços simples — a chave de casamento de nomes de seguradora/produto."""
    t = unicodedata.normalize("NFKD", str(texto or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", t).strip()


def casa_seguradora(nome: Any, lista: Iterable[str]) -> bool:
    """`nome` casa um item da lista quando o nome normalizado COMEÇA pela palavra do item ("Porto Seguro" ↔ "porto",
    "Itaú" ↔ "itau"). Começo de palavra, nunca substring solta ("Liberty" não casa "bert")."""
    alvo = normalizar(nome)
    for item in lista or ():
        chave = normalizar(item)
        if chave and (alvo == chave or alvo.startswith(chave + " ")):
            return True
    return False


def _mesclar(base: Any, extra: Any, caminho: str) -> Any:
    if isinstance(base, dict):
        if not isinstance(extra, Mapping):
            logger.warning("[MC-CONFIG] %s: esperado objeto — fica o padrão", caminho or "raiz")
            return base
        saida = dict(base)
        for k, v in extra.items():
            if k not in base:
                logger.info("[MC-CONFIG] chave desconhecida ignorada: %s.%s", caminho, k)
                continue
            # dicionários-tabela (vazios no padrão, ou de chaves livres) entram inteiros
            if isinstance(base[k], dict) and (not base[k] or k in _TABELAS_LIVRES):
                saida[k] = dict(v) if isinstance(v, Mapping) else base[k]
            else:
                saida[k] = _mesclar(base[k], v, f"{caminho}.{k}" if caminho else k)
        return saida
    if base is None:
        return copy.deepcopy(extra)
    if isinstance(base, bool):
        return extra if isinstance(extra, bool) else base
    if isinstance(base, (int, float)):
        if isinstance(extra, bool) or not isinstance(extra, (int, float)) or extra < 0:
            logger.warning("[MC-CONFIG] %s: número inválido — fica o padrão", caminho)
            return base
        return extra
    if isinstance(base, list):
        return list(extra) if isinstance(extra, list) else base
    if isinstance(base, str):
        return extra if isinstance(extra, str) else base
    return base


_TABELAS_LIVRES = frozenset({"por_seguradora", "desconto_permitido_pct"})

#: a TRAVA DE PRODUTO da régua da margem (conserto 130-A.1, red P2 / juiz 4): sem humano no laço (D-MC-68 corrigida),
#: um erro de config chegaria ao consumidor sem ninguém ver. O passo mínimo 💭 0,5 pp (abaixo disso o plano vira
#: centenas de recálculos — 📊 juiz 07/10: passo 0,01 → 504 passos). O piso mínimo é o do PRODUTO (`comissao.piso`).
PASSO_PP_MINIMO = 0.5


def _coerente(cfg: Dict[str, Any], pad: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """As réguas que não podem quebrar: piso ≤ autônomo ≤ entrada (todos > 0) · piso ≥ o piso do PRODUTO ·
    `PASSO_PP_MINIMO` ≤ passo ≤ entrada − autônomo · pesos somam 100 · opções ≥ 1. Fora disso: o padrão da seção.

    SPEC-131-0 F4: `pad` = de onde vem a seção quando a régua quebra. Na base da corretora é o padrão do produto; na
    sobreposição de um SERVIÇO é a base JÁ MESCLADA da corretora (um erro no manual da Renovação volta para a regra
    da corretora, nunca para o padrão do produto). O piso do PRODUTO vale sempre."""
    pad = pad if pad is not None else PADRAO_DO_PRODUTO
    c = cfg["comissao"]
    piso_do_produto = float(PADRAO_DO_PRODUTO["comissao"]["piso"])
    if not (0 < c["piso"] <= c["autonomo_minimo"] <= c["entrada"]) or not (0 < c["passo_pp"] <= c["entrada"]):
        logger.warning("[MC-CONFIG] comissão incoerente (piso ≤ autônomo ≤ entrada) — fica o padrão")
        cfg["comissao"] = copy.deepcopy(pad["comissao"])
    elif c["piso"] < piso_do_produto:
        # o Founder: "até 10 %" — a corretora pode SUBIR o piso dela, nunca descer abaixo do do produto
        logger.warning("[MC-CONFIG] piso da comissão abaixo do piso do produto — fica o padrão")
        cfg["comissao"] = copy.deepcopy(pad["comissao"])
    elif not (PASSO_PP_MINIMO <= c["passo_pp"] <= c["entrada"] - c["autonomo_minimo"]):
        # o passo desce "aos poucos, não direto": nunca menor que o mínimo, nunca maior que o trecho normal inteiro
        logger.warning("[MC-CONFIG] passo da comissão fora de [mínimo, entrada − autônomo] — fica o padrão")
        cfg["comissao"] = copy.deepcopy(pad["comissao"])
    pesos = cfg["nota"]["pesos"]
    if set(pesos) != set(pad["nota"]["pesos"]) or abs(sum(float(v) for v in pesos.values()) - 100.0) > 1e-6:
        logger.warning("[MC-CONFIG] pesos da nota não somam 100 — fica o padrão")
        cfg["nota"] = copy.deepcopy(pad["nota"])
    a = cfg["alvo_abaixo_da_atual_pct"]
    if not (0 <= a["minimo"] <= a["maximo"] < 100):
        cfg["alvo_abaixo_da_atual_pct"] = copy.deepcopy(pad["alvo_abaixo_da_atual_pct"])
    for k in ("no_whatsapp", "na_pagina"):
        if int(cfg["opcoes"][k]) < 1:
            cfg["opcoes"][k] = pad["opcoes"][k]
    if int(cfg["validade"]["padrao_dias"]) < 1:
        cfg["validade"]["padrao_dias"] = pad["validade"]["padrao_dias"]
    # SPEC-129-C — as tabelas por ramo: um valor fora da faixa vale o padrão DAQUELE ramo, nunca um número quebrado
    c = cfg["comissao"]
    if not (c["entrada"] <= c["teto_pct"] <= 100):
        logger.warning("[MC-CONFIG] comissao.teto_pct fora de [entrada, 100] — fica o padrão")
        cfg["comissao"] = copy.deepcopy(pad["comissao"])
    teto = float(cfg["comissao"]["teto_pct"])
    por_ramo = cfg["comissao"].get("por_ramo") or {}
    for r, v in list(por_ramo.items()):
        # red P4 (conserto 129-C): 0 não é comissão (é o padrão do Agger que a D-129C-05 evita) → volta à entrada
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v <= teto):
            logger.warning("[MC-CONFIG] comissao.por_ramo.%s inválida (fora de (0, teto]) — fica a entrada", r)
            por_ramo[r] = None
    reaj = cfg["renovacao"].get("reajuste_basica_pct") or {}
    for r, v in list(reaj.items()):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 100:
            logger.warning("[MC-CONFIG] renovacao.reajuste_basica_pct.%s inválido — fica o padrão", r)
            reaj[r] = (pad["renovacao"].get("reajuste_basica_pct") or {}).get(r)
    for tabela in ("preferencias_de_seguradoras", "coberturas_essenciais"):
        for r, lista in list((cfg.get(tabela) or {}).items()):
            cfg[tabela][r] = [i for i in lista if (isinstance(i, str) and i.strip())
                              or (isinstance(i, int) and not isinstance(i, bool))]
    return cfg


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-129-C — a config POR RAMO (as chaves do jsonb são o código do ramo como texto)
# ---------------------------------------------------------------------------------------------------------------------
def _do_ramo(tabela: Any, ramo: Any) -> Any:
    return (tabela or {}).get(str(int(ramo))) if isinstance(tabela, Mapping) else None


def comissao_do_ramo(config: Mapping[str, Any], ramo: Any) -> float:
    """D-129C-05: a comissão EXPLÍCITA do item no ramo; sem número próprio do ramo → `comissao.entrada`."""
    com = config.get("comissao") or PADRAO_DO_PRODUTO["comissao"]
    v = _do_ramo(com.get("por_ramo"), ramo)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return float(com["entrada"])


def teto_da_comissao(config: Mapping[str, Any]) -> float:
    """Red P4 (conserto 129-C): o teto da comissão explícita do item (`comissao.teto_pct`)."""
    com = config.get("comissao") or {}
    v = com.get("teto_pct")
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
        return float(v)
    return float(PADRAO_DO_PRODUTO["comissao"]["teto_pct"])


def reajuste_basica_pct(config: Mapping[str, Any], ramo: Any) -> Optional[float]:
    """D-129C-06: o reajuste da básica na renovação, em %. None = o ramo não tem a regra (o auto).

    SPEC-131-0 F4: aceita o MAPA por ramo (o formato do padrão) ou UM número só ("15 % em todos os ramos de RE") —
    um número vale para os ramos que o padrão conhece; o auto continua sem a regra."""
    tabela = (config.get("renovacao") or {}).get("reajuste_basica_pct")
    if isinstance(tabela, (int, float)) and not isinstance(tabela, bool):
        tabela = _reajuste_em_mapa(tabela)
    v = _do_ramo(tabela, ramo)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _reajuste_em_mapa(numero: float) -> Dict[str, float]:
    """Um número só → o mesmo número em cada ramo que o padrão do produto conhece."""
    return {r: numero for r in PADRAO_DO_PRODUTO["renovacao"]["reajuste_basica_pct"]}


def basica_renovada(config: Mapping[str, Any], ramo: Any, basica_anterior: Any) -> Optional[float]:
    """A básica do ano novo = a anterior + o reajuste do ramo (None sem regra ou sem valor anterior positivo).

    Chamador (SPEC-130-B F4): `pedido.de_apolice` → `_de_apolice_re`, que lê a Básica da FICHA da apólice e grava
    `risco.valor_basica = basica_renovada(...)` (marcada `assumido`). Sem regra de reajuste para o ramo → `None`, e o
    pedido sai com o aviso `sem_regra_de_reajuste` (a anterior NÃO vai "sem reajuste"). ⚠️ Quem DISPARA a renovação
    (o auxiliar da 131) ainda não chama `de_apolice` — o pedido fica pronto, o gatilho é da 131: ela é chamada pela 131
    através de `de_apolice`."""
    pct = reajuste_basica_pct(config, ramo)
    try:
        anterior = float(basica_anterior)
    except (TypeError, ValueError):
        return None
    if pct is None or anterior <= 0:
        return None
    return round(anterior * (1 + pct / 100), 2)


def preferencias_do_ramo(config: Mapping[str, Any], ramo: Any) -> list:
    """D-129C-07: a lista ORDENADA de seguradoras preferidas do ramo (nomes ou códigos do Agger); vazia = nenhuma."""
    return list(_do_ramo(config.get("preferencias_de_seguradoras"), ramo) or [])


def coberturas_essenciais(config: Mapping[str, Any], ramo: Any) -> tuple:
    return tuple(_do_ramo(config.get("coberturas_essenciais"), ramo) or ())


def _normalizar(linha: Mapping[str, Any]) -> Dict[str, Any]:
    """Os atalhos de escrita que o formato aceita, levados ao formato do padrão (sem tocar no dicionário de quem
    chamou): `renovacao.reajuste_basica_pct` como UM número → o mesmo número em cada ramo."""
    saida = dict(linha)
    ren = saida.get("renovacao")
    if isinstance(ren, Mapping):
        r = ren.get("reajuste_basica_pct")
        if isinstance(r, (int, float)) and not isinstance(r, bool):
            saida["renovacao"] = {**ren, "reajuste_basica_pct": _reajuste_em_mapa(r)}
    return saida


def _modo_valido(v: Any) -> bool:
    return isinstance(v, str) and v in MODOS


def _ramo_da_excecao(v: Any) -> Optional[str]:
    """O ramo como o jsonb guarda (o código como texto). Recusa bool, vazio e o que não é número de ramo."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int) and v > 0:
        return str(v)
    if isinstance(v, str) and v.strip().isdigit() and int(v.strip()) > 0:
        return str(int(v.strip()))
    return None


def _excecao(item: Any) -> Optional[Dict[str, Any]]:
    """Uma exceção do modo, limpa — ou None (fora do formato: ignorada com log). Tem de ter UMA condição ao menos."""
    if not isinstance(item, Mapping) or not _modo_valido(item.get("modo")):
        return None
    saida: Dict[str, Any] = {"modo": item["modo"]}
    if item.get("ramo") is not None:
        ramo = _ramo_da_excecao(item.get("ramo"))
        if ramo is None:
            return None
        saida["ramo"] = ramo
    v = item.get("valor_acima_de")
    if v is not None:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            return None
        saida["valor_acima_de"] = float(v)
    if "ramo" not in saida and "valor_acima_de" not in saida:
        return None
    return saida


def _servicos(bruto: Any) -> Dict[str, Dict[str, Any]]:
    """As chaves PRÓPRIAS de cada serviço (modo, exceções, e o que o serviço tem só dele), sobre o padrão. Fora do
    formato → o padrão daquela chave, com log. As sobreposições da BASE não entram aqui (`_sobreposicao`)."""
    saida = copy.deepcopy(PADRAO_DO_PRODUTO["servicos"])
    if bruto is None:
        return saida
    if not isinstance(bruto, Mapping):
        logger.warning("[MC-CONFIG] servicos: esperado objeto — fica o padrão")
        return saida
    for s, bloco in bruto.items():
        if s not in saida:
            logger.info("[MC-CONFIG] serviço desconhecido ignorado: servicos.%s", s)
            continue
        if not isinstance(bloco, Mapping):
            logger.warning("[MC-CONFIG] servicos.%s: esperado objeto — fica o padrão", s)
            continue
        alvo = saida[s]
        if "modo" in bloco:
            if _modo_valido(bloco["modo"]):
                alvo["modo"] = bloco["modo"]
            else:
                logger.warning("[MC-CONFIG] servicos.%s.modo inválido — fica o padrão", s)
        if "excecoes_do_modo" in bloco:
            lista = bloco["excecoes_do_modo"]
            if isinstance(lista, list):
                limpas = [e for e in (_excecao(i) for i in lista) if e is not None]
                if len(limpas) != len(lista):
                    logger.warning("[MC-CONFIG] servicos.%s.excecoes_do_modo: item fora do formato ignorado", s)
                alvo["excecoes_do_modo"] = limpas
            else:
                logger.warning("[MC-CONFIG] servicos.%s.excecoes_do_modo: esperado lista — fica o padrão", s)
        for k in _CHAVES_PROPRIAS[s] - {"modo", "excecoes_do_modo"}:
            if k in bloco:
                alvo[k] = _mesclar(alvo[k], bloco[k], f"servicos.{s}.{k}")
    _renovacao_coerente(saida["renovacao"])
    return saida


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-131-A F2 — a régua das chaves da MADRUGADA (`servicos.renovacao`): fora dela, o padrão DAQUELA chave, com log
# ---------------------------------------------------------------------------------------------------------------------
_HHMM = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
#: as faixas 💭 (valores iniciais; a corretora configura dentro delas)
ANTECEDENCIA_DIAS_FAIXA = (1, 60)
RETENTATIVA_MIN_FAIXA = (1, 360)
TETO_SESSOES_CORRETORA_FAIXA = (1, 20)
#: SPEC-132 (Founder 14/10: "no mínimo 30"): o teto OPCIONAL por conta por noite. Sem ele (null) o relógio decide
TETO_POR_CONTA_NOITE_FAIXA = (30, 500)
ANTECIPAR_ATE_DIAS_FAIXA = (0, 20)
COMISSAO_A_MAIS_PP_FAIXA = (0, 5)
#: SPEC-131-B (D-131-04) — "Com qual conta" a renovação calcula: a do responsável (padrão) ou SEMPRE a da corretora
CONTAS_DA_RENOVACAO = ("responsavel", "corretora")


def _inteiro_na_faixa(v: Any, faixa: tuple) -> bool:
    return _numero(v) and int(v) == v and faixa[0] <= v <= faixa[1]


def _opcoes_validas(v: Any) -> bool:
    from portal_worker.multicalculo.presets import OPCOES_DA_RENOVACAO, PROIBIDAS_NA_RENOVACAO

    return (isinstance(v, list) and 1 <= len(v) <= 3 and len(set(map(str, v))) == len(v)
            and all(isinstance(o, str) and o in OPCOES_DA_RENOVACAO and o not in PROIBIDAS_NA_RENOVACAO for o in v))


def _renovacao_coerente(bloco: Dict[str, Any]) -> None:
    pad = PADRAO_DO_PRODUTO["servicos"]["renovacao"]
    if not _inteiro_na_faixa(bloco.get("antecedencia_dias"), ANTECEDENCIA_DIAS_FAIXA):
        logger.warning("[MC-CONFIG] servicos.renovacao.antecedencia_dias fora de 1–60 — fica o padrão")
        bloco["antecedencia_dias"] = pad["antecedencia_dias"]
    else:
        bloco["antecedencia_dias"] = int(bloco["antecedencia_dias"])
    if not _opcoes_validas(bloco.get("opcoes")):
        logger.warning("[MC-CONFIG] servicos.renovacao.opcoes: 1 a 3 de anterior/franquia_reduzida/completa_mais — "
                       "fica o padrão")
        bloco["opcoes"] = list(pad["opcoes"])
    # SPEC-132: o teto por conta por noite é OPCIONAL — null (o padrão) = o relógio decide; um número só de 30 a 500.
    # Fora disso (o 12 antigo, 0, 10, texto) → null, com log: ⛔ nunca um teto abaixo de 30 chega à madrugada
    teto = bloco.get("teto_por_conta_noite")
    if teto is not None and not _inteiro_na_faixa(teto, TETO_POR_CONTA_NOITE_FAIXA):
        logger.warning("[MC-CONFIG] servicos.renovacao.teto_por_conta_noite fora de %s–%s — fica sem teto (o relógio "
                       "decide)", *TETO_POR_CONTA_NOITE_FAIXA)
        bloco["teto_por_conta_noite"] = pad["teto_por_conta_noite"]
    elif teto is not None:
        bloco["teto_por_conta_noite"] = int(teto)
    for chave, faixa in (("teto_sessoes_corretora", TETO_SESSOES_CORRETORA_FAIXA),
                         ("antecipar_ate_dias", ANTECIPAR_ATE_DIAS_FAIXA)):
        if not _inteiro_na_faixa(bloco.get(chave), faixa):
            logger.warning("[MC-CONFIG] servicos.renovacao.%s fora de %s–%s — fica o padrão", chave, *faixa)
            bloco[chave] = pad[chave]
        else:
            bloco[chave] = int(bloco[chave])
    v = bloco.get("comissao_a_mais_pp")
    if not (_numero(v) and COMISSAO_A_MAIS_PP_FAIXA[0] <= v <= COMISSAO_A_MAIS_PP_FAIXA[1]):
        logger.warning("[MC-CONFIG] servicos.renovacao.comissao_a_mais_pp fora de 0–5 — fica o padrão")
        bloco["comissao_a_mais_pp"] = pad["comissao_a_mais_pp"]
    else:
        bloco["comissao_a_mais_pp"] = float(v)
    if bloco.get("conta") not in CONTAS_DA_RENOVACAO:
        logger.warning("[MC-CONFIG] servicos.renovacao.conta: responsavel ou corretora — fica o padrão")
        bloco["conta"] = pad["conta"]
    bloco["janela"] = _janela_limpa(bloco.get("janela"))
    aceites = bloco.get("prosseguir_aceites")
    if not (isinstance(aceites, list) and all(isinstance(x, str) and _UUID.match(x.strip()) for x in aceites)):
        # ⛔ um aceite que não é um id NÃO liga a política em ninguém: a lista inteira volta a vazia (desligada)
        logger.warning("[MC-CONFIG] servicos.renovacao.prosseguir_aceites: esperada uma lista de ids — fica vazia")
        bloco["prosseguir_aceites"] = []
    else:
        bloco["prosseguir_aceites"] = sorted({x.strip().lower() for x in aceites})


def _janela_limpa(janela: Any) -> Dict[str, Any]:
    janela = janela if isinstance(janela, Mapping) else {}
    limpa: Dict[str, Any] = {}
    for k, padrao in PADRAO_DO_PRODUTO["servicos"]["renovacao"]["janela"].items():
        v = janela.get(k, padrao)
        ok = _inteiro_na_faixa(v, RETENTATIVA_MIN_FAIXA) if k == "retentativa_min" else \
            (isinstance(v, str) and bool(_HHMM.match(v)))
        if not ok:
            logger.warning("[MC-CONFIG] servicos.renovacao.janela.%s inválido — fica o padrão", k)
        limpa[k] = (int(v) if k == "retentativa_min" else v) if ok else padrao
    # 🔴 conserto C2 (red P4): o Prosseguir é SÓ da madrugada — `prosseguir_de` < `prosseguir_ate`, os dois dentro de
    # 00:00–07:00 local (a "noite" é uma só). Por quê: o padrão é 01:00–06:30 (D-131-29) e o desvio 06:15; com
    # `00:00–23:59` o meio-dia prosseguia e cabiam 2 Prosseguir no mesmo dia (📊 red team). Fora disso → as DUAS voltam
    # ao padrão (o motor aplica a mesma régua: `motor.prosseguir_na_madrugada`)
    m_de, m_ate = _minutos_hhmm(limpa["prosseguir_de"]), _minutos_hhmm(limpa["prosseguir_ate"])
    if not (0 <= m_de < m_ate <= LIMITE_DO_PROSSEGUIR_MIN):
        logger.warning("[MC-CONFIG] servicos.renovacao.janela.prosseguir_de/ate fora de 00:00–07:00 — fica o padrão")
        pad = PADRAO_DO_PRODUTO["servicos"]["renovacao"]["janela"]
        limpa["prosseguir_de"], limpa["prosseguir_ate"] = pad["prosseguir_de"], pad["prosseguir_ate"]
    # SPEC-132: a hora-limite de COMEÇAR um cálculo fica entre o calcular e a conferência (calcular < último ≤
    # conferir − 10 min, o pior pedido 📊 ~9 min). Fora disso → a conferência menos 10 min (nunca antes do calcular+1)
    limpa["ultimo_inicio"] = ultimo_inicio_coerente(limpa)
    return limpa


#: SPEC-132 — o pior pedido de renovação (📊 LAUDO-I1 §2.4: login 54 s + teto de leitura 480 s + logout 14 s = 548 s)
#: arredondado: quem começa na hora-limite termina antes da conferência
MARGEM_ATE_A_CONFERENCIA_MIN = 10


def ultimo_inicio_coerente(janela: Mapping[str, Any]) -> str:
    """`janela.ultimo_inicio` (HH:MM) se calcular < ele ≤ conferir − margem; senão conferir − margem (≥ calcular + 1)."""
    pad = PADRAO_DO_PRODUTO["servicos"]["renovacao"]["janela"]

    def m(k: str) -> int:
        v = janela.get(k)
        return _minutos_hhmm(v if isinstance(v, str) and _HHMM.match(v) else pad[k])

    calc, conf = m("calcular"), m("conferir")
    teto = conf - MARGEM_ATE_A_CONFERENCIA_MIN
    v = janela.get("ultimo_inicio")
    if isinstance(v, str) and _HHMM.match(v) and calc < _minutos_hhmm(v) <= teto:
        return v
    alvo = max(calc + 1, teto)
    return f"{alvo // 60:02d}:{alvo % 60:02d}"


#: conserto C2 (red P4): o fim da madrugada para o Prosseguir, em minutos locais (07:00)
LIMITE_DO_PROSSEGUIR_MIN = 7 * 60


def _minutos_hhmm(v: str) -> int:
    h, m = str(v).split(":")
    return int(h) * 60 + int(m)


def _resolver_renovacao(cfg: Dict[str, Any], bruto_servicos: Any) -> None:
    """UM número de antecedência nos dois lugares que o produto lê: `servicos.renovacao.antecedencia_dias` (o madrugada)
    e `renovacao.antecedencia_dias` (a tela, o manual). Quem vence: o que a corretora escreveu em
    `servicos.renovacao.antecedencia_dias` > o efetivo da base (com o que a tela gravou em
    `servicos.renovacao.renovacao`) > o padrão. Fora de 1–60 → o padrão."""
    bloco = (cfg.get("servicos") or {}).get("renovacao")
    if not isinstance(bloco, dict):
        return
    bruto = bruto_servicos.get("renovacao") if isinstance(bruto_servicos, Mapping) else None
    explicito = isinstance(bruto, Mapping) and "antecedencia_dias" in bruto \
        and _inteiro_na_faixa(bruto["antecedencia_dias"], ANTECEDENCIA_DIAS_FAIXA)
    if explicito:
        dias = int(bruto["antecedencia_dias"])
    else:
        base = (cfg.get("renovacao") or {}).get("antecedencia_dias")
        dias = int(base) if _inteiro_na_faixa(base, ANTECEDENCIA_DIAS_FAIXA) \
            else PADRAO_DO_PRODUTO["servicos"]["renovacao"]["antecedencia_dias"]
    bloco["antecedencia_dias"] = dias
    cfg.setdefault("renovacao", {})["antecedencia_dias"] = dias


def _bloco_da_renovacao(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return _bloco_do_servico(cfg, "renovacao")


def antecedencia_dias(cfg: Mapping[str, Any]) -> int:
    """D-131-01: a renovação é calculada quando vence em ≤ isto (dias)."""
    v = _bloco_da_renovacao(cfg).get("antecedencia_dias")
    return int(v) if _inteiro_na_faixa(v, ANTECEDENCIA_DIAS_FAIXA) \
        else PADRAO_DO_PRODUTO["servicos"]["renovacao"]["antecedencia_dias"]


def janela_da_renovacao(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """A janela da madrugada (HH:MM no fuso da corretora + `retentativa_min`); chave fora da régua → o padrão dela."""
    return _janela_limpa(_bloco_da_renovacao(cfg).get("janela"))


def opcoes_da_renovacao(cfg: Mapping[str, Any]) -> tuple:
    """As opções da renovação (1–3, na ordem do disparo). Fora da régua → as três do produto."""
    v = _bloco_da_renovacao(cfg).get("opcoes")
    return tuple(v) if _opcoes_validas(v) else tuple(PADRAO_DO_PRODUTO["servicos"]["renovacao"]["opcoes"])


def teto_sessoes_corretora(cfg: Mapping[str, Any]) -> int:
    """D-131-30: sessões do Agger ao mesmo tempo por corretora."""
    v = _bloco_da_renovacao(cfg).get("teto_sessoes_corretora")
    return int(v) if _inteiro_na_faixa(v, TETO_SESSOES_CORRETORA_FAIXA) \
        else PADRAO_DO_PRODUTO["servicos"]["renovacao"]["teto_sessoes_corretora"]


def comissao_a_mais_pp(cfg: Mapping[str, Any]) -> float:
    """D-131-16: quantos pp a opção `anterior` da renovação leva ACIMA da comissão do ano anterior (`per_c`).
    ⚠️ `renovacao.comissao_a_mais_pp` {mínimo, máximo} da base é o TEXTO do manual de negociação (D-MC-66), não este."""
    v = _bloco_da_renovacao(cfg).get("comissao_a_mais_pp")
    if not (_numero(v) and COMISSAO_A_MAIS_PP_FAIXA[0] <= v <= COMISSAO_A_MAIS_PP_FAIXA[1]):
        v = PADRAO_DO_PRODUTO["servicos"]["renovacao"]["comissao_a_mais_pp"]
    return float(v)


def teto_por_conta_noite(cfg: Mapping[str, Any]) -> Optional[int]:
    """SPEC-132: None = sem teto (o relógio da madrugada decide). Configurado: 30–500 renovações por conta do Agger por
    noite (só limita a ANTECIPAÇÃO; a que vence hoje sai sempre). Fora da faixa → None, nunca um teto abaixo de 30."""
    v = _bloco_da_renovacao(cfg).get("teto_por_conta_noite")
    return int(v) if v is not None and _inteiro_na_faixa(v, TETO_POR_CONTA_NOITE_FAIXA) \
        else PADRAO_DO_PRODUTO["servicos"]["renovacao"]["teto_por_conta_noite"]


def antecipar_ate_dias(cfg: Mapping[str, Any]) -> int:
    """D-131-33: o excedente da noite é antecipado para até isto de dias antes (nunca depois do vencimento)."""
    v = _bloco_da_renovacao(cfg).get("antecipar_ate_dias")
    return int(v) if _inteiro_na_faixa(v, ANTECIPAR_ATE_DIAS_FAIXA) \
        else PADRAO_DO_PRODUTO["servicos"]["renovacao"]["antecipar_ate_dias"]


def _sobreposicao(bruto: Any, servico: str) -> Dict[str, Any]:
    """O que o bloco do serviço SOBREPÕE da base (tudo que não é chave própria dele). `servicos` dentro de um serviço
    não existe (um serviço não reescreve o manual de outro)."""
    if not isinstance(bruto, Mapping):
        return {}
    bloco = bruto.get(servico)
    if not isinstance(bloco, Mapping):
        return {}
    return {k: v for k, v in bloco.items() if k not in _CHAVES_PROPRIAS[servico] and k != "servicos"}


def mesclar(linha: Optional[Mapping[str, Any]], servico: Optional[str] = None) -> Dict[str, Any]:
    """O padrão ⊕ a config de uma corretora ⊕ (com `servico`) o que o manual DAQUELE serviço sobrepõe — puro, é o que
    `carregar` usa depois de ler o banco. `servico=None` = a base da corretora (o comportamento de antes da 131-0).

    🔴 A separação: só o bloco `servicos[servico]` entra; o de outro serviço nunca (o guarda da F4 fica VERMELHO se
    a Renovação mudar o que o Quem Cobra Menos lê)."""
    if servico is not None and servico not in SERVICOS:
        raise ValueError(f"serviço desconhecido: {servico!r} (aceitos: {', '.join(SERVICOS)})")
    base = copy.deepcopy(PADRAO_DO_PRODUTO)
    linha = dict(linha or {})
    bruto_servicos = linha.pop("servicos", None)
    cfg = _coerente(_mesclar(base, _normalizar(linha), "")) if linha else base
    cfg["servicos"] = _servicos(bruto_servicos)
    if servico is not None:
        extra = _sobreposicao(bruto_servicos, servico)
        if extra:
            da_corretora = copy.deepcopy(cfg)
            cfg = _coerente(_mesclar(cfg, _normalizar(extra), f"servicos.{servico}"), da_corretora)
        # a config de UM serviço leva só o bloco DELE: o modo da Renovação não é dado do Quem Cobra Menos
        cfg["servicos"] = {servico: cfg["servicos"][servico]}
    _resolver_renovacao(cfg, bruto_servicos)          # SPEC-131-A: UMA antecedência, nos dois lugares
    return cfg


def carregar(company_id: str, db: Any = None, servico: Optional[str] = None) -> Dict[str, Any]:
    """A config EFETIVA da corretora: `PADRAO_DO_PRODUTO` ⊕ a linha dela em `multicalculo_config` ⊕ (com `servico`)
    o manual daquele serviço (`servicos[servico]` sobrepõe a base). `servico=None` = a base (o comportamento de hoje).

    🔴 Filtro `company_id` AQUI (o backend usa service role; a RLS sem policy não protege erro de filtro — §7).
    Sem linha → o padrão. Banco fora → `ConfigIndisponivel` (nunca o padrão às cegas: o piso dela pode ser maior)."""
    if db is None:
        raise TypeError("carregar precisa do banco (db=)")
    if servico is not None and servico not in SERVICOS:
        raise ValueError(f"serviço desconhecido: {servico!r} (aceitos: {', '.join(SERVICOS)})")
    cid = str(company_id or "").strip()
    if not _UUID.match(cid):
        raise ValueError("company_id precisa ser um uuid")
    cid = cid.lower()
    try:
        resp = db.table(TABELA).select("company_id, config").eq("company_id", cid).limit(1).execute()
    except Exception as exc:  # noqa: BLE001
        raise ConfigIndisponivel(f"multicalculo_config ilegível ({type(exc).__name__})") from None
    linhas = list(getattr(resp, "data", None) or [])
    linha = next((l for l in linhas if str(l.get("company_id", "")).lower() == cid), None)
    return mesclar((linha or {}).get("config") if linha else None, servico)


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-131-0 F4 — a chave calcular × entregar × negociar, por serviço (D-131-0-10/12)
# ---------------------------------------------------------------------------------------------------------------------
def _bloco_do_servico(cfg: Mapping[str, Any], servico: str) -> Mapping[str, Any]:
    if servico not in SERVICOS:
        raise ValueError(f"serviço desconhecido: {servico!r} (aceitos: {', '.join(SERVICOS)})")
    todos = cfg.get("servicos") if isinstance(cfg, Mapping) else None
    if not isinstance(todos, Mapping):
        return PADRAO_DO_PRODUTO["servicos"][servico]          # uma config sem a seção (crua): o padrão do produto
    bloco = todos.get(servico)
    if not isinstance(bloco, Mapping):
        # 🔴 a config foi carregada para OUTRO serviço: responder o padrão aqui seria adivinhar — recusa
        raise ValueError(f"esta config é de outro serviço ({', '.join(map(str, todos))}); carregue com "
                         f"servico={servico!r}")
    return bloco


def _casa(excecao: Mapping[str, Any], ramo: Any, valor: Any) -> bool:
    if "ramo" in excecao:
        if ramo is None or _ramo_da_excecao(ramo if not isinstance(ramo, float) else int(ramo)) != excecao["ramo"]:
            return False
    if "valor_acima_de" in excecao:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not valor > excecao["valor_acima_de"]:
            return False
    return True


def modo_do_servico(cfg: Mapping[str, Any], servico: str, ramo: Any = None, valor: Any = None) -> str:
    """O que o AutoBrokers faz NESTE serviço, para este ramo/valor: 'calcular' · 'calcular_entregar' ·
    'calcular_entregar_negociar'. Exceções que casam: vale a MAIS CONTIDA (a ordem em que foram escritas não decide);
    nenhuma casa: o `modo` do serviço. Modo fora da lista → o padrão do produto daquele serviço."""
    bloco = _bloco_do_servico(cfg, servico)
    modo = bloco.get("modo")
    if not _modo_valido(modo):
        modo = PADRAO_DO_PRODUTO["servicos"][servico]["modo"]
    casados = [e["modo"] for e in (_excecao(i) for i in (bloco.get("excecoes_do_modo") or ()))
               if e is not None and _casa(e, ramo, valor)]
    if casados:
        return min(casados, key=MODOS.index)
    return modo


def pode_entregar(cfg: Mapping[str, Any], servico: str, ramo: Any = None, valor: Any = None) -> bool:
    """O resultado do cálculo pode ir ao CLIENTE (não só ficar pronto no Agger)?"""
    return modo_do_servico(cfg, servico, ramo, valor) in ("calcular_entregar", "calcular_entregar_negociar")


def pode_negociar(cfg: Mapping[str, Any], servico: str, ramo: Any = None, valor: Any = None) -> bool:
    """O agente pode negociar (recalcular com margem/cortes) neste serviço?"""
    return modo_do_servico(cfg, servico, ramo, valor) == "calcular_entregar_negociar"


def conta_da_renovacao(cfg: Optional[Mapping[str, Any]]) -> str:
    """SPEC-131-B (D-131-04): `responsavel` (o Agger de quem cuida da apólice — padrão) ou `corretora` (sempre o da
    corretora). Lido por `qual_agger.decidir`. Sem config, ou fora do formato → o padrão do produto (`responsavel`)."""
    if cfg is None:
        return PADRAO_DO_PRODUTO["servicos"]["renovacao"]["conta"]
    v = _bloco_do_servico(cfg, "renovacao").get("conta")
    return v if v in CONTAS_DA_RENOVACAO else PADRAO_DO_PRODUTO["servicos"]["renovacao"]["conta"]


def conta_global_se_vence_em_dias(cfg: Mapping[str, Any]) -> int:
    """§5 F3 — a conta da corretora só assume a renovação de quem teve a senha recusada quando a apólice vence em
    MENOS que isto (lido por `qual_agger.decidir`). Fora do formato → o padrão do produto."""
    bloco = _bloco_do_servico(cfg, "renovacao")
    v = bloco.get("conta_global_se_vence_em_dias")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
        v = PADRAO_DO_PRODUTO["servicos"]["renovacao"]["conta_global_se_vence_em_dias"]
    return int(v)


# ---------------------------------------------------------------------------------------------------------------------
# SPEC-131-0 F4 — a ESCRITA pela tela "Serviços": só estas chaves; qualquer outra é RECUSADA (a leitura ignora, a
# escrita recusa — a tela nunca grava o que o produto não lê)
# ---------------------------------------------------------------------------------------------------------------------
#: o que a tela edita em cada serviço. O Quem Cobra Menos não entra: o manual dele é a natureza do canal (a comparação
#: usa a config do CANAL — `proposta.py`, `cfg_sol`) e a corretora não o reescreve por esta tela.
EDITAVEL_POR_SERVICO: Dict[str, frozenset] = {
    "cotacao": frozenset({"modo", "excecoes_do_modo", "preferencias_de_seguradoras",
                          # SPEC-132-B (D-132B-06) — o Configurar da Cotação Rápida edita SÓ estas regras do cálculo:
                          # quais opções, a comissão de ENTRADA e a validade (o resto aparece como "padrão do
                          # AutoBrokers"). `comissao` e `validade` são chaves da BASE sobrepostas só na cotação
                          # (`_sobreposicao`); `opcoes` é chave PRÓPRIA da cotação (`opcoes_da_cotacao`).
                          "opcoes", "comissao", "validade"}),
    "renovacao": frozenset({"modo", "excecoes_do_modo", "preferencias_de_seguradoras",
                            "conta_global_se_vence_em_dias", "renovacao",
                            # SPEC-131-B G3 — a aba Configurar da Renovação: quantas opções (1–3), o teto por conta
                            # por noite e a antecipação. São chaves que a MADRUGADA já lê (`opcoes_da_renovacao`,
                            # `teto_por_conta_noite`, `antecipar_ate_dias`): a tela nunca grava o que o produto não lê.
                            # ⛔ `prosseguir_aceites` e `teto_sessoes_corretora` continuam fora (só o comando/gerente).
                            "opcoes", "teto_por_conta_noite", "antecipar_ate_dias",
                            # SPEC-131-B G5 — "Com qual conta" (D-131-04): lida por `qual_agger.decidir`
                            "conta"}),
}
_EDITAVEL_NA_RENOVACAO = frozenset({"antecedencia_dias", "reajuste_basica_pct"})
#: as faixas que a tela aceita 💭 (fora delas a escrita é recusada; nunca um número quebrado gravado)
#: SPEC-131-A: a mesma faixa da leitura (`ANTECEDENCIA_DIAS_FAIXA`, 1–60) — 📊 0 linhas em `multicalculo_config`
#: (SELECT count(*), 12/10): nenhum valor salvo fica fora dela
ANTECEDENCIA_DIAS_MAX = 60
CONTA_GLOBAL_DIAS_MAX = 60


def _numero(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _erros_das_preferencias(v: Any, onde: str) -> list:
    if not isinstance(v, Mapping):
        return [f"{onde}: esperado um objeto por ramo"]
    erros = []
    ramos = PADRAO_DO_PRODUTO["preferencias_de_seguradoras"]
    for r, lista in v.items():
        if r not in ramos:
            erros.append(f"{onde}.{r}: ramo desconhecido")
        elif not isinstance(lista, list) or not all(
                (isinstance(i, str) and i.strip()) or (isinstance(i, int) and not isinstance(i, bool)) for i in lista):
            erros.append(f"{onde}.{r}: esperada uma lista de seguradoras")
    return erros


#: SPEC-132-B — os CÁLCULOS que a cotação aceita (a `minima` é só do canal; a `padrao` é obrigatória: dela sai a
#: Recomendada) e as faixas que a tela da cotação aceita 💭 (fora delas a escrita é recusada)
OPCOES_DA_COTACAO = ("padrao", "economica", "completa_mais")
VALIDADE_DIAS_FAIXA = (1, 30)
#: a comissão de ENTRADA da cotação: do autônomo do produto + 1 passo (a régua `_coerente` exige espaço para negociar)
#: até o teto do produto
COMISSAO_ENTRADA_FAIXA = (float(PADRAO_DO_PRODUTO["comissao"]["autonomo_minimo"])
                          + float(PADRAO_DO_PRODUTO["comissao"]["passo_pp"]),
                          float(PADRAO_DO_PRODUTO["comissao"]["teto_pct"]))


def _opcoes_da_cotacao_validas(v: Any) -> bool:
    return (isinstance(v, list) and 1 <= len(v) <= 3 and len(set(map(str, v))) == len(v)
            and all(isinstance(x, str) and x in OPCOES_DA_COTACAO for x in v) and "padrao" in v)


def opcoes_da_cotacao(cfg: Optional[Mapping[str, Any]]) -> tuple:
    """SPEC-132-B — os cálculos da cotação, na ORDEM do disparo (a de `OPCOES_DA_COTACAO`, nunca a de quem escreveu).
    Sem config, ou fora da régua → o padrão do produto."""
    pad = tuple(PADRAO_DO_PRODUTO["servicos"]["cotacao"]["opcoes"])
    if cfg is None:
        return pad
    v = list(_bloco_do_servico(cfg, "cotacao").get("opcoes") or [])
    if not _opcoes_da_cotacao_validas(v):
        return pad
    return tuple(o for o in OPCOES_DA_COTACAO if o in v)


def pagina_da_cotacao(cfg: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """SPEC-132-B — os textos da página de VENDA: {diferenciais: [str], depois_do_sim: [str], faq: [{pergunta,
    resposta}]}. Cada lista da corretora vale INTEIRA quando está no formato; fora dele (ou vazia, salvo
    `diferenciais`), o padrão do produto daquela lista — nunca uma lista quebrada na página do cliente."""
    pad = PADRAO_DO_PRODUTO["servicos"]["cotacao"]["pagina"]
    bloco: Mapping[str, Any] = {}
    if cfg is not None:
        bloco = _bloco_do_servico(cfg, "cotacao").get("pagina") or {}
        if not isinstance(bloco, Mapping):
            bloco = {}

    def textos(v: Any) -> Optional[list]:
        if isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v):
            return [x.strip() for x in v]
        return None

    saida: Dict[str, Any] = {}
    dif = textos(bloco.get("diferenciais"))
    saida["diferenciais"] = dif if dif is not None else list(pad["diferenciais"])
    dep = textos(bloco.get("depois_do_sim"))
    saida["depois_do_sim"] = dep if dep else list(pad["depois_do_sim"])
    faq = bloco.get("faq")
    if (isinstance(faq, list) and faq and all(isinstance(i, Mapping) and str(i.get("pergunta") or "").strip()
                                              and str(i.get("resposta") or "").strip() for i in faq)):
        saida["faq"] = [{"pergunta": str(i["pergunta"]).strip(), "resposta": str(i["resposta"]).strip()} for i in faq]
    else:
        saida["faq"] = [dict(i) for i in pad["faq"]]
    return saida


def erros_da_edicao(servicos: Any = None, preferencias_de_seguradoras: Any = None) -> list:
    """A escrita da tela "Serviços": a lista de erros (vazia = pode gravar). Recusa chave fora da lista, serviço que
    a tela não edita, modo fora dos três, exceção sem condição, número fora da faixa."""
    erros: list = []
    if preferencias_de_seguradoras is not None:
        erros += _erros_das_preferencias(preferencias_de_seguradoras, "preferencias_de_seguradoras")
    if servicos is None:
        return erros
    if not isinstance(servicos, Mapping):
        return erros + ["servicos: esperado um objeto"]
    for s, bloco in servicos.items():
        if s not in EDITAVEL_POR_SERVICO:
            erros.append(f"servicos.{s}: este serviço não se edita por esta tela")
            continue
        if not isinstance(bloco, Mapping):
            erros.append(f"servicos.{s}: esperado um objeto")
            continue
        for k, v in bloco.items():
            onde = f"servicos.{s}.{k}"
            if k not in EDITAVEL_POR_SERVICO[s]:
                erros.append(f"{onde}: chave fora da lista")
            elif k == "modo" and not _modo_valido(v):
                erros.append(f"{onde}: escolha um dos três modos")
            elif k == "excecoes_do_modo":
                if not isinstance(v, list):
                    erros.append(f"{onde}: esperada uma lista")
                    continue
                for i, item in enumerate(v):
                    if not isinstance(item, Mapping) or set(item) - {"ramo", "valor_acima_de", "modo"} \
                            or _excecao(item) is None:
                        erros.append(f"{onde}[{i}]: precisa de um modo e de um ramo e/ou um valor")
            elif k == "preferencias_de_seguradoras":
                erros += _erros_das_preferencias(v, onde)
            elif k == "conta_global_se_vence_em_dias":
                if not _numero(v) or not 0 <= v <= CONTA_GLOBAL_DIAS_MAX or int(v) != v:
                    erros.append(f"{onde}: um número inteiro de dias, de 0 a {CONTA_GLOBAL_DIAS_MAX}")
            elif k == "conta":
                if v not in CONTAS_DA_RENOVACAO:
                    erros.append(f"{onde}: escolha {' ou '.join(CONTAS_DA_RENOVACAO)}")
            elif k == "opcoes" and s == "cotacao":
                # SPEC-132-B: a MESMA régua da leitura (`opcoes_da_cotacao`) — ⛔ a mínima é do canal
                if not _opcoes_da_cotacao_validas(v):
                    erros.append(f"{onde}: de 1 a 3 opções da cotação ({', '.join(OPCOES_DA_COTACAO)}), sem "
                                 "repetir e com a padrao")
            elif k == "opcoes":
                # a MESMA régua da leitura (`_opcoes_validas`): ⛔ econômica e mínima nunca numa renovação
                if not _opcoes_validas(v):
                    erros.append(f"{onde}: de 1 a 3 opções da renovação, sem repetir")
            elif k == "comissao":
                # SPEC-132-B: só a ENTRADA (o piso, o autônomo e o passo são do padrão do AutoBrokers)
                if not isinstance(v, Mapping) or set(v) != {"entrada"}:
                    erros.append(f"{onde}: só a comissão de entrada ({{\"entrada\": %}}) se edita aqui")
                elif not _numero(v["entrada"]) or not COMISSAO_ENTRADA_FAIXA[0] <= v["entrada"] <= COMISSAO_ENTRADA_FAIXA[1]:
                    erros.append(f"{onde}.entrada: um percentual de {COMISSAO_ENTRADA_FAIXA[0]:g} a "
                                 f"{COMISSAO_ENTRADA_FAIXA[1]:g}")
            elif k == "validade":
                if not isinstance(v, Mapping) or set(v) != {"padrao_dias"}:
                    erros.append(f"{onde}: só os dias de validade ({{\"padrao_dias\": n}}) se editam aqui")
                elif not _inteiro_na_faixa(v["padrao_dias"], VALIDADE_DIAS_FAIXA):
                    erros.append(f"{onde}.padrao_dias: um número inteiro de dias, de {VALIDADE_DIAS_FAIXA[0]} a "
                                 f"{VALIDADE_DIAS_FAIXA[1]}")
            elif k == "teto_por_conta_noite":
                # SPEC-132: null = sem teto (o relógio decide); um número, só de 30 para cima — "nunca só 12"
                if v is not None and not _inteiro_na_faixa(v, TETO_POR_CONTA_NOITE_FAIXA):
                    erros.append(f"{onde}: sem limite, ou um número inteiro de {TETO_POR_CONTA_NOITE_FAIXA[0]} a "
                                 f"{TETO_POR_CONTA_NOITE_FAIXA[1]} (o mínimo é {TETO_POR_CONTA_NOITE_FAIXA[0]} por "
                                 "noite)")
            elif k == "antecipar_ate_dias":
                if not _inteiro_na_faixa(v, ANTECIPAR_ATE_DIAS_FAIXA):
                    erros.append(f"{onde}: um número inteiro de dias, de {ANTECIPAR_ATE_DIAS_FAIXA[0]} a "
                                 f"{ANTECIPAR_ATE_DIAS_FAIXA[1]}")
            elif k == "renovacao":
                if not isinstance(v, Mapping):
                    erros.append(f"{onde}: esperado um objeto")
                    continue
                for kk, vv in v.items():
                    onde2 = f"{onde}.{kk}"
                    if kk not in _EDITAVEL_NA_RENOVACAO:
                        erros.append(f"{onde2}: chave fora da lista")
                    elif kk == "antecedencia_dias":
                        if not _numero(vv) or not 1 <= vv <= ANTECEDENCIA_DIAS_MAX or int(vv) != vv:
                            erros.append(f"{onde2}: um número inteiro de dias, de 1 a {ANTECEDENCIA_DIAS_MAX}")
                    elif kk == "reajuste_basica_pct":
                        mapa = _reajuste_em_mapa(vv) if _numero(vv) else vv
                        if not isinstance(mapa, Mapping):
                            erros.append(f"{onde2}: um número ou um número por ramo")
                            continue
                        for r, pct in mapa.items():
                            if r not in PADRAO_DO_PRODUTO["renovacao"]["reajuste_basica_pct"]:
                                erros.append(f"{onde2}.{r}: ramo sem reajuste da básica")
                            elif not _numero(pct) or not 0 <= pct <= 100:
                                erros.append(f"{onde2}.{r}: um percentual de 0 a 100")
    return erros


def validade_dias(config: Mapping[str, Any], seguradoras: Iterable[str]) -> int:
    """D-MC-71: a MENOR validade entre as seguradoras do quadro (dias por seguradora na config; senão o padrão)."""
    val = config["validade"]
    tabela = {normalizar(k): v for k, v in (val.get("por_seguradora") or {}).items()}
    dias = [int(tabela.get(normalizar(s), val["padrao_dias"])) for s in seguradoras]
    return min(dias) if dias else int(val["padrao_dias"])


def e_produto_de_assinatura(seguradora: Any, produto: Any, config: Mapping[str, Any]) -> bool:
    seg, prod = normalizar(seguradora), normalizar(produto)
    for regra in config.get("produtos_de_assinatura") or ():
        if not isinstance(regra, Mapping):
            continue
        s, p = normalizar(regra.get("seguradora")), normalizar(regra.get("produto"))
        if (s and seg == s) or (p and p in prod):
            return True
    return False
