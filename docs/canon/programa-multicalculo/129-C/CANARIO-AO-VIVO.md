# SPEC-129-C — o canário AO VIVO (1 pedido por ramo)

> 📊 11/10/2026, 06:15:08–06:20:11 UTC (03:15–03:20 de Brasília), relógio desta máquina. Branch `spec/129-C-mais-ramos`,
> HEAD `c6fbba5`. Autorização: Founder em 10/10 (D-129C-09). Script e saídas brutas ficam no rascunho do canário, fora do git.
> ⛔ Este documento não tem CPF, CNPJ, nome nem endereço: só ids internos, códigos de seguradora e valores de prêmio/LMI.

## 1. Como rodou
- **Pela PORTA**: `MulticalculoProvider.calcular(company_id = Resulta, corretoras = [Resulta], opcoes = ("padrao",),
  origem = "teste")`, com `AUTOBROKERS_CANARIO=1` só neste processo. A comissão (📊 15 %) foi a que a porta tirou da config
  do ramo (`comissao_do_ramo`). As coberturas foram as da opção `padrao` (`presets.coberturas_re`), com a básica do pedido
  e **sem extras** da apólice (o canário mede o preset, que é o que o produto manda).
- **O MOTOR REAL** local (molde: `backend/scripts/multicalculo_canario.py` da 129-B): `Motor(..., canario=True,
  somente_pedidos={os 3 pedidos})`, `uma_volta()` até o cálculo terminar, Chromium local com `PORTAL_HEADLESS_MODE=classic`.
  Um motor para os 3 ramos, um após o outro: **1 login e 1 logout**.
- **A conta**: a `agger-da-corretora` da Resulta (`f64ea768…`, `robo_estado=ativo`, janela nula = 24x7). O motor a
  escolheu sozinho. ⚠️ Ao contrário do script da 129-B, este canário **não** pausa a conta nem apaga a senha no fim: é a
  conta do produto, que fica sempre ligada. Só o logout.
- **Renovação**: tratada como seguro novo nos 3 ramos (sem os 4 campos da tela), como pedido.
- Instrumentos (nada muda no produto): um contador de `disparar` (= `calcularV2`), uma escuta em `Sessao.avaliar` que guarda
  o resumo do preparo (códigos de seguradora), o status do POST e o tamanho da lista de atividades, e uma escuta em
  `escolher_atividades`.

### Os riscos usados e o que foi ASSUMIDO
| ramo | canário (intake) | básica (LMI de incêndio da apólice) | o que a apólice trouxe | o que foi ASSUMIDO (padrão da tela medido, fixture `formulario_*`) |
|---|---|---:|---|---|
| 16 Condomínio | `conv-9789d6e0ee0f` (apólice Tokio) | 📊 R$ 17.600.000 | endereço do risco, tipo Residencial, Vertical, sem elevador, valor de novo | `ano_fundacao` "2005" (a tela não tem padrão; é o valor de uma gravação saneada) · `blocos` "1" e `pavimentos` "1" (padrão da tela) · `protecoes` [Extintores] (padrão da tela) |
| 2 Residencial | `cffc0a6ea2` (HDI Em Casa; a data de nascimento veio da proposta da mesma pasta) | 📊 R$ 100.000 | endereço, Casa, Habitual, construção Superior, Prédio + Conteúdo, valor de novo | `sexo` omitido (o robô manda o "M" da tela) · `proprietario` marcado (padrão da tela) |
| 18 Empresarial | `63b746709f` (proposta Sura de loja desocupada, atípica) | 📊 R$ 911.000 | endereço, atividade "edifícios desocupados", valor de novo, extintor | `pavimento` Térreo · `localizacao` Outros · `construcao` Sólida · `objeto` Prédio + Conteúdo (todos padrão da tela) |

⚠️ FATO: os dois canários de residencial apontados (`cffc0a6ea2` e `1ee68aee40`) e o do empresarial são apólices e propostas
emitidas pela **AutoFleet**, não pela Resulta. O cálculo saiu na conta da Resulta, como a tarefa pedia. Escolhi o
`cffc0a6ea2` porque a proposta dele traz a data de nascimento, que é obrigatória no residencial; a apólice da Porto não traz.

## 2. O resultado, por ramo
| | 16 Condomínio | 2 Residencial | 18 Empresarial |
|---|---|---|---|
| pedido aceito pela porta | ✅ (nada faltou pelo contrato) | ✅ | ✅ |
| `calcularV2` | 📊 1 · **HTTP 201** | 📊 1 · **HTTP 201** | 📊 1 · **HTTP 201** |
| seguradoras no corpo | 📊 **7**: 1 · 4 · 5 · 8 · 11 · 32 · 35 | 📊 **8**: 1 · 3 · 4 · 5 · 7 · 8 · 11 · 12 | 📊 **1**: 5 (as outras 9 saíram por "sem atividade compatível") |
| responderam com preço | 📊 3 | 📊 3 | 📊 1 |
| recusaram (família) | Porto **CREDENCIAL** · HDI **CREDENCIAL** (e depois deu preço, ver §3.3) · Tokio, Chubb e Bradesco **DESCONHECIDA** | HDI, Porto e Mapfre **CREDENCIAL** · Bradesco **DADO** · Zurich **ACEITACAO** | — (as 9 sem atividade são narradas como `sem_atividade_compativel`) |
| do POST ao último preço (`t_s` do robô) | 📊 46 s (fechou o conjunto em 70 s) | 📊 48 s (fechou em 82 s) | 📊 47 s |
| da reserva ao `fechado` (relógio desta máquina) | 📊 134 s (inclui o login de 📊 54 s) | 📊 90 s | 📊 61 s (inclui a busca da atividade) |
| menor prêmio | 📊 Allianz **R$ 8.408,79** | 📊 Tokio **R$ 490,25** | 📊 Allianz **R$ 2.072,76** |
| ranking da `comparacao.comparar` (comparáveis) | Allianz | Tokio · Allianz · Yelum | Allianz |
| produto diferente (fora do ranking) | HDI R$ 8.914,17 · Axa R$ 14.471,12 | — | — |
| `resumo` da comparação | cotadas 7 · comparáveis 1 · diferentes 2 · sem preço 4 · régua `re` | cotadas 8 · comparáveis 3 · diferentes 0 · sem preço 5 | cotadas 10 · comparáveis 1 · diferentes 0 · sem preço 9 |
| status final | `fechado` | `fechado` | `fechado` |

O que a apólice de referência pagava (💭 só para dar ordem de grandeza, porque as coberturas não são as mesmas): condomínio
📊 R$ 8.934,20 (Tokio, com outro desenho de coberturas) e residencial 📊 R$ 654,32 (HDI, LMIs extras menores que os do preset).

⚠️ Os relógios: o banco está 📊 ~86 s **atrás** desta máquina (cabeçalho `Date` do Supabase 06:19:09 contra 06:20:35 local,
na mesma hora). `criado_em` dos eventos é do banco; `disparado_em`, `primeira_oferta_em` e `fechado_em` são desta máquina. Por
isso os tempos acima usam `t_s`, o relógio do robô a partir do POST, ou só colunas desta máquina. Nunca misture as duas.

## 3. O que divergiu do que os testes previam
1. **Nenhum erro de contrato no Agger.** Os 3 POSTs voltaram 201: nenhuma chave recusada, nenhum 400, nenhuma validação. Não
   apareceu nada sobre os campos `*Txt` nem sobre `seguradoCpfCnpj`. ⚠️ INFERÊNCIA: o corpo foi aceito como está, mas isso
   não prova que cada campo foi lido como o robô pretendia (o Agger aceita chave a mais calado).
2. **Empresarial: a atividade derrubou 9 de 10 seguradoras.** A busca `getOptionsBySegFull` com o termo "edificios desocupados"
   (o único que `termos_de_busca` gera, porque a atividade não cai em nenhuma das 5 classes) devolveu 📊 15 blocos de
   seguradora, mas **1 opção no total**: "Edifícios desocupados" da Allianz (casamento exato). As outras 9 saíram com o evento
   `sem_atividade_compativel`, como o desenho manda (nunca um código errado). 💭 Cada seguradora dá outro nome a esse risco
   ("imóvel desocupado", "prédio vazio"…), e um termo só não o encontra. O desenho funcionou, mas com 1 termo por atividade
   a cobertura do ramo é estreita fora das 5 classes. Fica para o gerente decidir. ⚠️ O evento grava `familia = DADO`, e a
   comparação mostra `SEM_ATIVIDADE_COMPATIVEL` para o mesmo fato: duas famílias para uma coisa.
3. **HDI no condomínio: recusou e cotou.** 📊 Evento 183 `seguradora_recusou | 4 | CREDENCIAL` em `t_s` 6 s, e evento 188
   `nova_oferta | 4` em 42 s, no mesmo cálculo. 💭 São dois produtos da HDI (um com a credencial inválida já conhecida, §11 da
   PROVA, e outro que respondeu); o leitor registra os dois. Quem lê só "recusou por credencial" erra.
4. **CREDENCIAL é a recusa que mais aparece no RE.** Porto (16 e 2), Mapfre (2) e HDI (16 e 2). Em 10/10 o §11 da PROVA dava
   13 de 14 credenciais válidas (só a HDI inválida), mas lá a medição foi do automóvel. 💭 Porto e Mapfre podem exigir
   credencial própria para RE. 🧑 Precisa ser conferido nas Configurações → Seguradoras da conta.
5. **DESCONHECIDA sem motivo guardado.** No condomínio, Tokio (a seguradora da apólice atual), Chubb e Bradesco recusaram com a
   família DESCONHECIDA. A tabela `multicalculo_eventos` **não tem coluna de motivo** (📊 colunas: `tipo, seguradora,
   seguradora_codigo, familia, chave, t_s, pacote, tipo_de_pacote…`), então o porquê se perdeu. Para o RE, que é novo, o
   leitor ainda não classifica essas mensagens.
6. **As seguradoras devolveram coberturas diferentes das pedidas** (comparando a linha `coberturas` do cálculo com a da oferta):
   - condomínio HDI: **sem** impacto de veículos e **sem** RC condomínio, com RC síndico 600 mil (pedido 300 mil) e vendaval
     134 mil (pedido 84 mil). Axa: **sem** RC síndico, com RC condomínio 600 mil (pedido 300 mil). Allianz: igual ao pedido.
     A comparação acertou ao tirar HDI e Axa do ranking ("produto diferente").
   - residencial: as 3 ofertas vieram **idênticas** ao pedido.
   - empresarial Allianz: **tirou** roubo (13,7 mil) e vidros (4,6 mil) e **acrescentou** danos morais 62,5 mil, RC
     empregador 125 mil, tumultos 91,1 mil e recomposição de documentos 45,55 mil. 🔴 Mesmo assim saiu como "comparável",
     porque com uma oferta só a referência da régua RE é ela mesma. Com 1 resposta, "comparável" não diz nada: o corretor não
     é avisado de que roubo e vidros sumiram.
   - O valor de `assist24hs` volta como TEXTO da seguradora ("Plano Plus", "COMPLETO"…), e `valorDeNovo` às vezes como 1, às
     vezes como "Sim". O preset manda código.
7. **Nenhum PDF guardado.** 📊 `tem_pdf = true` nas 7 ofertas, mas `pdf_path` vazio nas 7. Log: "pdfs: 2 não copiados"
   (condomínio), "3" (residencial), "1" (empresarial): a cópia DENTRO da página falhou em 6 de 7. 💭 O 7º PDF (condomínio)
   foi baixado, mas não chegou ao armazenamento: este processo não tem as variáveis do MinIO, então é INFERÊNCIA. No RE, a
   `porta.pdf` não entrega nada hoje.
8. **O corpo do residencial e do condomínio levou menos seguradoras do que `SEGURADORAS_DO_RAMO`.** Residencial: 8 das 15
   listadas, condomínio: 7 das 8 (a 19 saiu). É o cruzamento com as ativas da conta, como desenhado. Registro só para quem
   esperava 15.
9. Ponto positivo: a guarda barrou só telemetria de terceiros e `usuarioSalvarPreferencias` (o mesmo de 10/10). Não houve aviso
   de sessão ativa e não houve recarga entre telas durante o cálculo. O logout passou pela tela, como o produto faz.

## 4. O fim
- **Logout:** ✅ 📊 `deslogaSessao` **201** às 06:20:10 (log `multicalculo.sessao conta=f64ea768… logout 201`).
- **Sessões soltas:** 📊 **0**. A conta `agger-da-corretora` da Resulta ficou com `robo_estado = ativo`, `robo_dono = null` e a
  senha mantida, de propósito. As 4 contas-robô do Agger ficaram todas sem dono; as duas `canario-129b` seguem `pausado`.
- `calcularV2` no total: 📊 **3** (1 por ramo, só a opção padrão). Nada foi apagado. Nenhuma mensagem foi enviada a ninguém.
  Nenhuma "Excluir cotação".

### Os pedidos de teste criados (origem `teste`, corretora Resulta, ficam no banco e no Agger da Resulta)
| ramo | `multicalculo_pedidos.id` | `multicalculo_calculos.id` | negócio no Agger (`negocio_ref`) |
|---|---|---|---|
| 16 | `ec7b378c-d518-498c-a5e0-bc83298c8fd6` | `f573a41a-4006-49f4-b177-b5f8f8b2674e` | `d5cc8451-b7da-44ac-8305-4a738199e1dc` (versão 1) |
| 2 | `8fd2501b-0154-487c-a476-fb89772c2bbd` | `1cabfbaa-a133-49d1-bedb-36a9c0f0c278` | `85fc2ffb-045d-469a-9a2a-b492e5422e45` (versão 1) |
| 18 | `19d4b085-3e6e-4662-a397-802847c1d997` | `5363beca-5233-497b-bcd5-e999189efc24` | `34aadda5-b97a-485d-a049-d70092191976` (versão 1) |

Eventos 📊 183–191 (16), 192–200 (2), 201–209 e 219–220 (18). Ofertas: 📊 3 + 3 + 1.

## 5. O G7 da SPEC ("1 cálculo real por ramo, ofertas lidas, nenhuma exceção, logout")
FATO: **cumprido** nos 3 ramos. 1 cálculo por ramo, as 7 ofertas lidas pela `porta.consultar`, `comparar` rodou sem exceção,
o logout saiu 201. RECOMENDAÇÃO para o gerente, sem consertar nada aqui: (a) a régua RE com uma oferta só (§3.6); (b) o
motivo da recusa DESCONHECIDA não é guardado (§3.5); (c) os PDFs do RE (§3.7); (d) os termos de busca da atividade fora das
5 classes (§3.2); (e) conferir as credenciais de RE da Porto e da Mapfre (§3.4, 🧑 Founder ou corretora).
