modelo: claude-opus-5-5

# SPEC-131-0-B3 — Um WhatsApp só por pessoa (o pareado é o "WhatsApp de trabalho") + abas instantâneas + Custos em português

> **v1.0 · 15/10/2026** · redator Opus 5.5 (gerente) · branch `spec/131-0-B3-um-whatsapp` (da `origin/main` `6d3d911`) · AAA v13 ·
> **CRÍTICO** (pela soma). Fonte: as palavras do Founder de 15/10 · [B2](SPEC-131-0-B2-a-linha-do-usuario.md) e o relatório dela ·
> D-1310B3-01..03 (decididas pelo gerente de 15/10). 📊 medido · 💭 ilustrativo.

## 0. EXECUTION CARD
```
OUTCOME ........ a pessoa pareia o WhatsApp na aba "WhatsApp de trabalho" e ESSE número passa a ser o de tudo: a conversa com o
                 AutoBrokers, o "Quero renovar" que o cliente toca, a Situação da equipe. Quem não pareia informa só o número
                 (reserva). Trocar de aba num aplicativo fica instantâneo (sem ida ao servidor). "Tokens" e "Even" saem da tela
                 Custos, que passa a dizer a verdade. E o Raio-X / Radar de Renovações lê a InfoCap pela CONEXÃO da corretora
                 (hoje: só funciona para quem tem variável de ambiente com o nome — 📊 a Amandus recebeu "sem credencial" pela linha).
RISCO .......... 7 · o SEGURADO vê o número 3 · estado/estrutura 2 · todo uso 2
SUPERFÍCIE ..... 2 · vários comportamentos em lugares que listo
PISO ........... CRÍTICO pela soma (nada ENVIA: o envio a clientes é da 135 — D-1310B3-02)
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · juiz de design com capturas ≥ 90 · confirmação se blocker
O FIO .......... §2 · `backend/tests/test_spec1310b3_o_fio.py` = 1ª entrega da F1, VERMELHO
PARALELISMO .... F1 ‖ F2 ‖ F3 ‖ F4 ‖ F5 (arquivos disjuntos, §5) → costura (F2 lê o contrato da F1)
GATES .......... fio · 2 corretoras · mutações §6 · next build UMA vez + test:rotas-montam + next start + requisições · tsc · bateria
O ELO .......... "o Quero renovar abre o PAREADO porque a linha está conectada" → o fio atravessa integrations → número → página
FAIXA .......... 💭 4–6 h
```

## 1. O contrato
**Muda:** (a) a aba WhatsApp de trabalho (`/dashboard/configuracoes?aba=whatsapp`): o pareamento (QR) é o principal; conectado, "este é o
seu WhatsApp de trabalho" + para que serve HOJE e o que vem DEPOIS; o número digitado vira "Não quer conectar? Informe só o número";
(b) UM ponto do número de trabalho efetivo no backend, lido pelo "Quero renovar", pelo Meu perfil e pela Situação da equipe; (c) as abas
dos aplicativos trocam no navegador; (d) a tela Custos em português, sem "Even", sem número que mente; (e) Raio-X e Radar pela conexão.
**Não pode mudar:** nada vai a CLIENTE (135) · o número de ATENDIMENTO e o do QCM · a IDENTIDADE do atalho central (132-C:
`verificacao.py` e `envio._telefone_verificado` continuam no número DIGITADO e verificado — quem fala com o central prova o número que
declarou; a linha é outra porta) · o link direto `?aba=` e o "voltar" do navegador · o razão de créditos e a cobrança (SPEC-062).

## 2. O FIO
```
aba WhatsApp → Conectar → QR → integrations (purpose='linha_do_usuario', dono, paired_phone_e164, is_active, channel_status) →
perfil_do_membro.numero_de_trabalho(db, company_id, user_id) → {e164, origem: 'linha'|'digitado'|None} →
  ├ proposta.membro_para_o_cliente → página de renovação/venda → botão "Quero renovar" → wa.me/<PAREADO>
  ├ perfil_do_membro.ler_perfil → BFF /api/dashboard/meu-perfil → MeuWhatsAppDeTrabalho ("este é o seu WhatsApp de trabalho")
  └ perfil_do_membro.situacao_da_equipe → BFF /api/dashboard/equipe/situacao → SituacaoDaEquipe ("WhatsApp conectado")
Radar: chat/linha → RadarDeRenovacoesTool._arun → InfocapAnalyticsProvider._abrir (tenant_connections da corretora) → FonteInfocap
Abas: TabsTrigger → trocar() → window.history.pushState → useSearchParams (Next 15) → aba nova, ZERO requisição
```

## 2.1 BLOCO 0 (📊 15/10/2026, gerente)
| # | premissa | medição | o que muda no desenho |
|---|---|---|---|
| M0 | a linha funciona em produção? | `messages` da conversa `whatsapp_assistente` do RAFAEL: 22:52 pergunta → 22:53 resposta (33 s); 22:59 áudio → resposta (40 s); marca `boas_vindas:` 22:50:57 + id do GO | nada a consertar antes; T-178 cumprida no essencial (M2 notifica? M3 RAM: ficam) |
| M1 | `=1` liga para todos? | `estado.py:12-14` e `_quem_esta_ligado` → `None` = todas as pessoas | D-1310B3-03 já aplicada pelo Founder (15/10 noite) |
| M2 | quem lê o número de trabalho? | `git grep -n whatsapp_trabalho -- backend/app app` → `proposta.py:1246` (Quero renovar), `perfil_do_membro.py:219/344/376`, `atalho/verificacao.py` + `atalho/envio.py:376` (identidade do central — NÃO muda) | um ponto em `perfil_do_membro`; três leitores trocam |
| M3 | por que o Radar disse "sem credencial"? | `relatorios_comerciais.py:600,907` → `FonteInfocap.para_empresa(slug)` → `CORP_INFOCAP_{SLUG}_*`; o resolver por conexão existe em `infocap_analytics_provider.py:_abrir` | F5 troca o caminho (P-094-LEGADO) |
| M4 | por que a aba demora? | `AbasDoAplicativo.tsx:115` `router.push(?aba=)` numa página `force-dynamic` que NÃO lê `searchParams` (`[slug]/page.tsx`) → o servidor refaz a página inteira à toa | `history.pushState` (Next ≥ 14.1 sincroniza `useSearchParams`) |
| M5 | o que a tela Custos mostra? | `credit_transactions`: 📊 2 linhas no total, última 21/06 · `token_usage_logs` 30 dias: 📊 8.963 chamadas, **7.908 sem company_id**, **0 com details.user_id** · `UsageClient.tsx` "Tokens (30 dias)" · `tenant-usage-store.ts:21` rotula o atendimento "Even" | F4: fala o que é medido; o medidor sem corretora vira pendência da 062 |

## 3. Dados
Sem migration. As colunas existem (`company_members.whatsapp_trabalho_*`, `integrations.paired_phone_e164/owner_user_id/linha_*`).

## 4. O desenho
**A aba WhatsApp de trabalho** (`MeuWhatsAppDeTrabalho` + `MinhaLinhaDoWhatsApp`):
- *Linha disponível, não conectada* → título "Seu WhatsApp de trabalho" · "Conecte o WhatsApp que você usa com os clientes. Ele passa a ser
  o seu número de trabalho no AutoBrokers." · **[Conectar meu WhatsApp]** (QR). Abaixo, discreto: "Não quer conectar? Informe só o
  número" (o formulário de hoje, recolhido; aberto se já houver número digitado e nenhuma linha).
- *Conectada* → "✓ Este é o seu WhatsApp de trabalho — {número mascarado} · desde {data}". **Para que ele serve hoje:** conversar com o
  AutoBrokers (em "Mensagem para você"); é o número que o cliente recebe no "Quero renovar". **Quando a sua corretora ligar:** avisos do
  AutoBrokers · cobrança e renovação aos clientes. **Fica de fora:** o atendimento aos segurados continua no número da corretora. Se houver
  número digitado DIFERENTE: "O número {mascarado} que você informou antes fica guardado como reserva." [Desconectar].
- *Linha indisponível para esta pessoa* (chave) → o formulário de hoje como principal (o digitado é o número de trabalho).
- Todo texto que ficou falso corrigido (§9.3), e o teste que afirmava o texto antigo MIGRA, não morre.
**O número efetivo (um ponto):** `numero_de_trabalho` = o PAREADO quando há linha `is_active` com estado conectado da pessoa NAQUELA
corretora (`estado.linha_do_dono`); senão o DIGITADO confirmado; senão nenhum. Não depende da chave `LINHA_DO_USUARIO_LIGADA` (o número é
da pessoa; a chave governa a conversa, não a posse — D-1310B3-04).
**Abas instantâneas:** `trocar()` usa `window.history.pushState` (e `replaceState` onde hoje é `router.replace`) para mudanças SÓ de query
(`aba`, `item`); `router.push` fica para mudança de rota; `router.refresh` depois de instalar continua. Antes/depois medido no
`next start` (§6).
**Custos:** "Tokens" sai; entra o que a pessoa entende ("Respostas e leituras da IA", e a nota "a IA lê e escreve em pedaços de texto;
1.000 desses ≈ 750 palavras"); por assistente (nome humano: o CORE = "AutoBrokers", o de atendimento = o nome dele no banco, nunca
"Even"); por modelo com rótulo humano ("OpenAI · GPT-6 Luna"); dinheiro só do razão (`credit_transactions`) — sem lançamentos: "A cobrança
por uso ainda não começou na sua conta." Nunca converter custo de provedor em reais (seria preço — CLAUDE.md §13.6).

## 5. Fatias (cada arquivo, UM dono)
| fatia | entrega | arquivos |
|---|---|---|
| **F1 · o número efetivo** | `numero_de_trabalho` + os 3 leitores + o fio | `backend/app/services/perfil_do_membro.py` · `backend/app/services/multicalculo/proposta.py` (só `membro_para_o_cliente`) · `backend/tests/test_spec1310b3_o_fio.py` (NOVO) |
| **F2 · a aba** | redesenho + BFF + Situação da equipe | `components/perfil/{MeuWhatsAppDeTrabalho,MinhaLinhaDoWhatsApp}.tsx` · `components/perfil/useMeuPerfil.ts` · `app/api/dashboard/meu-perfil/route.ts` · `app/api/dashboard/equipe/situacao/route.ts` · `app/dashboard/personalizacao/corretora/equipe/SituacaoDaEquipe.tsx` · `app/dashboard/configuracoes/page.tsx` (só texto) · teste `.test.mjs` NOVO |
| **F3 · abas** | troca no navegador | `components/aplicativos/casca/AbasDoAplicativo.tsx` · `app/dashboard/auxiliares/[slug]/AuxiliarDetalheClient.tsx` · `components/aplicativos/cotacao/AbaCotacoes.tsx` · `components/aplicativos/renovacao/AbaRenovacoes.tsx` · teste `.test.mjs` NOVO |
| **F4 · Custos** | português + dado honesto | `app/dashboard/personalizacao/corretora/custos/{UsageClient,page}.tsx` · `lib/admin/tenant-usage-{store,view}.ts` · teste NOVO |
| **F5 · Radar pela conexão** | Raio-X e Radar pelo resolver da 094 | `backend/app/agents/tools/relatorios_comerciais.py` · `backend/tests/test_spec1310b3_radar_pela_conexao.py` (NOVO) |

**Contrato F1 → F2:** `ler_perfil(...)["whatsapp_trabalho"]` ganha `efetivo: {numero: e164|None, origem: 'linha'|'digitado'|None}`;
`situacao_da_equipe(...)["pessoas"][i]` ganha `whatsapp_trabalho_origem: 'linha'|'digitado'|None` e `whatsapp_trabalho_confirmado` passa a
ser verdadeiro também com a linha. O BFF repassa sem inventar.

## 6. A régua
**Mutações (cada guarda NOVO vermelho uma vez; restaura por cópia):** (1) `numero_de_trabalho` ignora a linha → o fio cai no digitado ·
(2) linha de OUTRA corretora da mesma pessoa vira o número desta · (3) linha desconectada/inativa continua valendo · (4) o atalho central
passa a aceitar o pareado como identidade (`test_spec132c_verificacao` tem de seguir verde sem mudança) · (5) `trocar()` volta a chamar
`router.push` · (6) Radar volta a `para_empresa` sem a bandeira legada · (7) "Even"/"Tokens" na tela.
**Isolamento:** duas corretoras reais (a pessoa com linha na A e número digitado na B: A → pareado, B → digitado).
**§9.1:** `npm run test:rotas-montam` + `next build` (UMA vez) + `next start` + `GET /api/dashboard/meu-perfil` (401 sem sessão) +
`GET /dashboard/configuracoes` responde. **Antes/depois das abas:** o tempo da requisição RSC que o `router.push` disparava
(`GET /dashboard/auxiliares/<slug>?aba=x` com `RSC: 1`, sessão real) × ZERO requisições na troca nova.
**Design:** juiz de design com capturas (claro/escuro, 390 px e 1280 px) da aba nos 3 estados e da tela Custos ≥ 90.

## 7. Decisões desta SPEC
| # | decisão | nota | contra |
|---|---|---|---|
| D-1310B3-01 | Um número só: o PAREADO é o WhatsApp de trabalho; o digitado é reserva de quem não pareia | 90 | dois números 30 |
| D-1310B3-02 | Envio a clientes pela linha fica na 135 (motor de envio humano); aqui só tela e dados prontos | 88 | ligar já 25 |
| D-1310B3-03 | A linha abre para todos (`=1`) depois do teste do Founder — 📊 o Founder já pôs `=1` em 15/10 e o teste passou (M0) | 85 | manter lista 50 |
| D-1310B3-04 | O efetivo não depende da chave da linha: depende da linha CONECTADA naquela corretora | 85 | depender da chave 55 (desligar a conversa trocaria o número do cliente) |
| D-1310B3-05 | A identidade do atalho central continua no número digitado e verificado | 90 | aceitar o pareado no central 40 (outra porta, outra prova) |
| D-1310B3-06 | Abas por `history.pushState` (Next 15) | 90 | tirar `force-dynamic` 40 (o servidor refaria igual) · biblioteca de rota rasa 20 |
| D-1310B3-07 | Raio-X e Radar pelo resolver da conexão (094); o legado só com `COMERCIAL_RESOLVER_LEGADO` | 92 | criar `CORP_INFOCAP_AMANDUS_*` 10 (fere §13.9) |
| D-1310B3-08 | Custos: dinheiro só do razão; uso em português; nunca custo de provedor em reais | 90 | converter USD→BRL 25 (é preço: §13.6, §10.2) |
| D-1310B3-09 | O medidor gravado sem corretora (📊 7.908/8.963) vai para a SPEC de cobrança (062), não aqui | 80 | consertar aqui 45 (Ledger/Billing, §5) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://nextjs.org/docs/app/building-your-application/routing/linking-and-navigating#using-the-native-history-api** · faz:
   `window.history.pushState/replaceState` integram ao roteador do App Router e sincronizam `useSearchParams` · modelamos: trocar a aba sem
   ida ao servidor · rejeitamos: `router.push` para mudar só a query · juiz: aba trocada sem requisição na aba Rede / no `next start`.
2. **https://www.radix-ui.com/primitives/docs/components/tabs** · faz: Tabs controlado (`value`/`onValueChange`) · modelamos: o valor
   vem do estado do navegador, não do servidor · rejeitamos: remontar a casca a cada troca · juiz: `AbasDoAplicativo.tsx`.
3. **https://pkg.go.dev/go.mau.fi/whatsmeow/store#Device** · faz: a identidade da conta pareada (`ID`, o JID do dono) vem da sessão, não
   do que alguém digitou · modelamos: o número de trabalho = o da sessão pareada · rejeitamos: o digitado como verdade quando há
   pareamento · juiz: mutação 1.
4. **https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them** · faz: explica token ≈ 4 caracteres ≈ ¾ de
   palavra · modelamos: a nota em português na tela Custos · rejeitamos: o número cru de tokens como métrica do corretor · juiz: mutação 7.

## 9. O QUE SAI (com destino)
Envio a clientes pela linha → 135 · avisos do sistema (desligados, `AVISOS_WHATSAPP_LIGADO`) → T-182 · o medidor sem corretora → 062
(pendência nova) · M2 (notifica?) e M3 (RAM por instância) da B2 → continuam em P-1310B2-01.
