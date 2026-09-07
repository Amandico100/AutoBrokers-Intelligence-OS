<!-- SANITIZADO em 07/09/2026 pelo orquestrador (EXTRA-001 RP0): telefones de teste substituidos pelos aliases TESTE-A/TESTE-B; os valores reais ficam na configuracao privada (BILLING_CANARIO_ALLOWLIST / ATTENDANT_INBOUND_ALLOWLIST). SHA-256 dos bytes de ENTRADA: 12ff4737dda231bfc929db71b2ef2dd706254ecc2383a7f9466b8be645e2b9f3 -->
# PROMPT DE ABERTURA — SPEC-EXTRA-001

> Cole este documento inteiro em um chat NOVO do Claude Code Fable, aberto na árvore atualizada do AutoBrokers. Este é um prompt privado: contém os dois números autorizados pelo Founder. Não commitar/publicar esses números. Instalar cópia sanitizada no canon e conservar a allowlist no mecanismo privado apropriado.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001 · Operação dos pilotos**, co-líder técnico com o Founder Amandus. Você será o executor do processo completo: investigar, validar a proposta, convertê-la em SPEC definitiva, aquecer o executor, implementar, provar, integrar e entregar, segundo `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA vigente**. A baseline desta preparação usa **v11.2 + OPÇÃO B de `DECISAO-DO-RITMO-03-09-2026.md`**.

**Não comece a SPEC-099.** O Founder priorizou esta EXTRA para fechar cobrança e preservar atendimento nos pilotos Resulta e AutoFleet. O lote linear 099–114 fica temporariamente pausado, sem renumeração e sem cancelamento. Vamos trabalhar uma SPEC por chat.

## 1. A tarefa e os arquivos recebidos

O pacote anexo contém:

1. `SPEC-EXTRA-001-operacao-dos-pilotos.md` — PROPOSTA, ainda não SPEC aprovada.
2. `SPEC-EXTRA-001-operacao-dos-pilotos-RESEARCH-PACK.md` — fontes, achados, limites e roteiro de remedição.
3. Este prompt.
4. `LEIA-ME-EXTRA-001.md` — uso pelo Founder e mapa dos destinos.
5. `MANIFESTO-SHA256.txt` — integridade dos arquivos acima.

Local esperado do projeto do Founder:
`C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`

Confirme a árvore real, branch e `origin/main`; não confie no nome da pasta. Se os anexos estiverem em Downloads ou numa pasta de entrada, localize os arquivos fornecidos sem varrer dados pessoais. Valide os hashes dos originais antes de sanitizar e instalar as cópias no canon. Não peça ao Founder para preencher proposta ou redesenhar o plano: esse é seu trabalho de conversão.

Destinos:

```text
docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos.md
docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos-RESEARCH-PACK.md
docs/canon/PROMPT-DE-ABERTURA-EXTRA-001-PREENCHIDO.md
docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md             ← VOCÊ cria a definitiva
docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md               ← VOCÊ inicia e preenche
```

Os dois primeiros arquivos são proposta/research, não execução. Não os sobrescreva para fingir que a proposta já estava validada. Mudanças na conversão vão para a SPEC definitiva e para a matriz de premissas corrigidas. Se já existir EXTRA-001 na árvore local, compare sua origem e estado antes de substituir qualquer coisa.

## 2. Autorizações atuais do Founder — leia antes de delegar

O Founder autorizou você a executar o processo desta SPEC e usar **somente estes números para testes de WhatsApp**:

```text
TESTE-A: [TESTE-A · allowlist privada] → +55TESTE-A
TESTE-B: [TESTE-B · allowlist privada] → +55TESTE-B
```

Ele informou que TESTE-A já esteve pareado na Resulta Seguros e na Amandus Seguros. **Confira o telefone realmente conectado hoje. Nome de corretora, instância ou propósito não prova identidade.**

**Não há autorização para usar os números operacionais pareados da Resulta ou da AutoFleet.** Não usar esses números nem como remetentes para testes enviados ao Founder. Não contatar Saionara, Regina, clientes, seguradoras ou grupos de suporte. Essa restrição vale para texto, boleto, resposta do agente, alerta, fallback, fila, retry e jobs de fundo.

Teste vivo permitido: remetente real e destinatário ambos pertencem à allowlist, são participantes distintos e estão no tenant/conversa/run de canário conferidos. Não trate duas conexões do mesmo número como dois telefones independentes. Não crie pareamento concorrente que derrube uma sessão existente.

Não ligue atendimento/auxiliar/dispatch globalmente numa corretora operacional. Pode habilitar **somente o canário isolado e seus participantes** quando a trava no ponto final de efeito estiver provada, impedindo mensagens ou acionamentos fora do escopo. Se não existe essa limitação seletiva, implemente-a antes de qualquer teste vivo. Não relaxe controles para testar.

Não abra chamado, sinistro ou assistência real e não envie a seguradoras, mesmo se um cliente de teste pedir guincho. Prove coordenação/roteamento com efeito externo bloqueado e o restante do atendimento no canal autorizado. Agger/cotações/renovações não são desta sessão.

Pode usar dados sintéticos e documentos sem validade financeira no canário; não alterar boleto real, copiar dados entre corretoras ou publicar dados de cliente. Consultas e obtenção de documento existente em portais seguem acessos e autoridade do projeto; nenhum ato externo além desse escopo é deduzido da frase “execute tudo”.

**Esta autorização limitada atual substitui a proibição antiga de qualquer mensagem somente para o canário descrito. Não substitui a proibição de usar linhas operacionais.** Investigador, pesquisador, aquecimento e juízes continuam read-only e sem envios. Inclua esta fronteira em cada pacote de execução.

Não commitar os dois números acima. Use aliases no canon/relatório/dossiê; mantenha valores reais em contexto/configuração privada. Não expor credenciais, CPF, nome de cliente, apólice, placa, número completo, boleto, signed URL ou transcript sensível em logs/evidências públicas.

## 3. Estado herdado — não confundir com medição de hoje

- Repositório: `Amandico100/AutoBrokers-Intelligence-OS`.
- Baseline remota lida na preparação em 07/09/2026: `34424fa576f8fdb35f687e3a3af5c66a6e07f915`. A revisão da execução pode ter avançado.
- Última SPEC do lote: **098 · Cada coisa sabe de quem é**, com relatório em `docs/canon/reports/SPEC-098-EXECUTION-REPORT.md`.
- O prompt antigo 099 contém status e medições históricos de deployment. Não copie “deploy pendente/endpoint 200” sem verificar; leitura de health não prova versão instalada.
- Código observado: `live` de cobrança ainda termina em aviso de desativado; UI oferece `test` e `none`; composição atual de teste tem prefixos/sufixos; dedup lê histórico antes do envio e registra depois; falha da leitura retorna vazio; texto pode ser aceito com PDF falho. **Reproduza antes de corrigir.**
- Há coordenação existente: `context_note_for` é injetado no atendimento; a identidade canônica do WhatsApp principal reúne observer/attendance/dispatch. `observer` não significa necessariamente “não atende”. Não recrie conexão para mudar label.
- Preserve a herança da 098: tenant ativo resolvido no servidor, vínculo do ator revalidado no efeito, run/artefato/conversa, escritores únicos e schema vivo.

## 4. Bootstrap enxuto e obrigatório

Leia primeiro o núcleo de sessão: `CLAUDE.md`, `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`, `docs/canon/GLOSSARIO.md`; confira a OPÇÃO B em `docs/canon/DECISAO-DO-RITMO-03-09-2026.md`. Depois proposta e research pack desta EXTRA. Para subagentes, use os pacotes vivos e somente núcleo AAA §0–§3, §5 e §7.3 + contrato/arquivos/gates pertinentes, conforme o protocolo.

Consulte por demanda:

- 078 para a cobrança; 095 para Artifact/Delivery; 097/097.1 para caso, finalização e atendimento; 098 para identidade/autoridade.
- `MIGRATIONS-AUTHORITY.md` antes de qualquer SQL.
- `SPEC-EXECUTION-REPORT-TEMPLATE.md` para abrir o relatório.
- `INDICE-DE-SPECS.md`, `ESTADO-DAS-SPECS.md`, `EXECUTION-MASTER-PLAN.md` somente nas seções de fila/estado afetadas.
- Pendências por número: `P-098-FILA-SEM-EXPIRE`, `P-098-RUN-NOS-JOBS`, `P-098-FICHA-RMW`, `P-097-TELEFONE-BR-DUPLICADO`, `P-098-UNIT-B-NA-SUITE`, `P-098-FIXTURE-NOT-NULL` e as da 078 efetivamente tocadas.

Não leia `PENDENCIAS.md` inteiro nem todo o canon. Propostas antigas 097/098 citadas em prompts podem existir só localmente; não invente seu conteúdo nem paralise esta EXTRA porque não vieram no remoto.

## 5. Como começar e converter

1. Preflight Git: fetch, SHA HEAD/origin/main, contagem atrás/à frente, branch, status. Preserve mudanças locais e respeite a autoridade de worktree; não delete trabalho para “limpar”.
2. RP0: verifique o manifesto e o SHA-256 do research pack. Sanitização de telefone no prompt/proposta altera o hash desses arquivos: registre hashes de entrada e das cópias canônicas, sem esconder a transformação.
3. Inicie relatório pelo template, abrindo com EXECUTION CARD dentro do limite do guarda, e calcule risco/superfície. **Piso CRÍTICO**, sem rebaixar para economizar tokens.
4. Investigador + pesquisador em um papel: remedir código/banco/contratos e reabrir as três fontes primárias do RP. Leia funções e chamadores até o efeito; mostre o ELO, não duas contagens desconectadas.
5. Converta em SPEC executável com BLOCO 0, mapa de unidades coesas, gates e MUTAÇÃO por bloco, seção “O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS” com 3–7 URLs reabertas, “O QUE SAIU” com gatilhos, pendências e caixa do Founder.
6. Não crie painel de juízes para a proposta. Faça uma rodada de aquecimento do executor em contexto limpo, emende a SPEC e execute na mesma sessão desta EXTRA.

## 6. Aquecimento — perguntas para preencher com a revisão medida

Use `docs/canon/pacotes/PACOTE-AQUECIMENTO.md`. Entregue 10–15 perguntas. A lista abaixo fornece 14; o orquestrador adapta as coordenadas ao código atual. Perguntas 1 e 2 são falsas deliberadas do exercício, **não regras do projeto**; se uma premissa tiver deixado de ser falsa após mudanças locais, substitua-a por outra falsa medida antes de enviar ao aquecimento.

1. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** “A rotina `live` já envia o boleto; basta expor a opção na UI.” Refute pelo caminho executável atual.
2. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** “O índice único gravado depois do envio garante que dois workers nunca enviem a mesma cobrança.” Mostre o entrelaçamento que contradiz essa afirmação.
3. O modo humano é semanticamente igual a approval? Quem consome a aprovação hoje?
4. Uma integração `observer` pode alimentar atendimento? Qual condição realmente decide o consumo do inbound?
5. Como provar que o número autorizado é o remetente real e continua sendo no replay? O que ocorre se ele for substituído por um número operacional?
6. Em quais pontos texto, PDF, retorno, alerta e fallback podem escapar da autorização? Liste todos que encontrou.
7. Qual estado representa texto aceito e PDF falho? Qual representa timeout sem confirmação?
8. Como a mesma parcela mantém identidade entre dois dias, dois runs, modos diferentes e seguradoras diferentes?
9. Por que uma atendente receber o pacote não permite concluir que o cliente recebeu? Como conciliar mudança para direto?
10. Como contexto sobrevive quando muitos outros clientes recebem mensagens? Como evita atribuir os casos dos clientes ao número da atendente?
11. Como testa atendimento e mudança de assunto sem ligar tenant operacional nem abrir chamado na seguradora?
12. Reproduza três premissas/medições da SPEC, com comando/consulta e resultado redigido sem PII.
13. Liste o que você NÃO entendeu ou não conseguiu provar; “entendi tudo” não satisfaz o exercício.
14. Ache um defeito material não apontado pela proposta, ou informe onde procurou e não encontrou. Entregue nota e card que você aplicaria.

Não inserir respostas prontas no pacote de quem deve investigar. Permissões não são pegadinha: a allowlist e a proibição de linhas operacionais permanecem inequívocas.

## 7. O que você deve entregar como produto

- **Equipe:** pacote final limpo, com texto copiável e PDF correto; contexto interno separado e cliente ainda não marcado como entregue.
- **Direto:** documento do item e contato validados; caminho completo governado, sem texto de teste.
- **Histórico:** reserva concorrente, tentativas por componente e reexecução segura. Não repetir parcela no mesmo dia/dias seguintes; reenvio legítimo tem motivo. Troca de modo não reinicia permissão.
- **Respostas:** usar atendimento existente com contexto correto; tratar dúvida, já paguei, segunda via, contestação, destinatário errado e preferência de contato; sem inventar pagamento/negociação.
- **Convivência:** um responsável por resposta, takeover humano preservado, observador/QR intactos, prioridade de atendimento e nenhuma mistura com URA de seguradora.
- **Falhas:** incidentes duráveis no painel e avisos honestos; se WhatsApp morreu, não dizer “humano avisado” por uma tentativa falha no mesmo canal.
- **UI:** escolhas e estados reais, compatibilidade do legado, configuração sem ativação automática.
- **Provas:** matriz G00–G23 da proposta, pares mínimos, mutações nomeadas, gate zero, canário autorizado e regressão pertinente.

Não crie outro motor, scheduler, inbox, sender ou ledger universal. Evolua as autoridades existentes. Contrato mínimo de conexão/expiração necessário à cobrança entra aqui; email, Meta, segundo QR e Channel Fabric completo ficam para a 099.

## 8. Execução AAA sem desperdício e sem atalhos

CRÍTICO opção B: desenhista antes do código; builder por unidade coesa; verificador mecânico; duas lentes (verdade/regressão e produto/DADO) + red team independentes; conserto conjunto; juiz fresco confirma e audita. Papéis/modelos conforme o protocolo e disponibilidade efetiva; registre o que realmente usou.

Use `schema_vivo.json` e schema atual para dublês; não invente colunas. Mutação por cópia em subprocesso com falha nova identificável, sem mutar árvore de outro escritor; restaure por cópia. Não use `xfail` para esconder processo perigoso. Gate zero vermelho antes de implementar, depois verde pelo comportamento real.

Suite inteira conforme gates do protocolo e risco, com árvore parada; parciais no ciclo curto. Baseline com falhas exige demonstração na base e no head, triagem nominal e tratamento de regressão; não rotular toda falha de “preexistente”. Mudou rota Next/configuração pertinente: `test:rotas-montam`, aplicação iniciada e request real conforme o canon.

Um escritor por arquivo; contratos compartilhados integram serialmente. Nunca `git add -A`, force push ou exclusão automática de lock. Timeout não prova que o dono do lock morreu. Salve conserto completo e retomável antes do próximo. Não deixe agentes ativos escrevendo durante mutações/gates finais.

Orçamento no card, medição real de tokens, telemetria e faixa de relógio. Se a janela interromper, preserve checkpoint com SHA, arquivos, gates, próximas ações e nenhuma rotina de teste solta. Não substitua esta EXTRA por outra SPEC “leve” para gastar a janela. Prossiga nos checkpoints da mesma entrega quando houver recursos.

## 9. Dossiê e acompanhamento — responsabilidade explícita

O Founder acompanha aqui:
https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868

Fonte versionada:
`docs/canon/reports/dossies/dossies-autobrokers.html`

Você ou um subagente documental deve atualizar a fonte **durante a execução e a cada bloco fechado**, com um escritor por arquivo. Preserve páginas existentes. Acrescente página EXTRA-001, navegação e linha na home. A baseline usa páginas `<section class="page" id="p-…">` e router derivado do DOM; confira antes de escolher `p-extra001`.

Atualize fase, status dos blocos, gates, provas, falhas materiais, próximos passos, implantação e caixa do Founder. Não faça contagem “no ar” baseada apenas em commits. Resultado de canário não é aceite das atendentes. Use aliases dos números de teste.

Conforme o prompt 099, **leia o HTML publicado inteiro antes de republicar com `url`**, usando a ferramenta disponível, e confira o resultado no link. Se não houver ferramenta/acesso, mantenha fonte atualizada, diga explicitamente “publicação do dossiê pendente” e entregue ao Founder o HTML e o passo exato; não finja que atualizou o artifact e não crie substituto silencioso.

Registre fila em INDICE, ESTADO-DAS-SPECS, EXECUTION-MASTER-PLAN e memória existente. Verifique se guardas/indexadores só reconhecem números: a família EXTRA deve ser submetida aos mesmos gates, não isentada. Preserve 099–114 com seus números; não crie 115 para esta entrega.

## 10. Integração, produção e estado final

Avance até o resultado completo autorizado. Push somente de commits gateados na main conforme o canon, com SHA/saída real e verificação remota. Se main avançar, não force: integre e valide o head efetivo.

Implantação respeita autorização e procedimento vigentes. Se depender do clique do Founder no EasyPanel, entregue pacote pronto e passos exatos para esse único ato final. Não contorne a autoridade por API. Ordem dos serviços é decidida pelo contrato medido desta SPEC, não copiada do histórico.

Canário usa exclusivamente TESTE-A/TESTE-B. Se faltar QR/ação física/acesso indispensável, complete tudo que independe disso e registre gate não comprovado, sem declarar produção validada. Não ativar operação nas linhas Resulta/AutoFleet. O Founder conduzirá validação com Saionara/Regina usando os números de teste; prepare o roteiro sem contatá-las.

No final entregue:

1. O que mudou para a corretora e como usar cada modalidade.
2. SPEC definitiva, relatório, SHAs, migrations e VERIFY/ROLLBACK quando houver.
3. Quais gates passaram, quais dependem de ação física e o que não foi comprovado.
4. Estado separado: implementado / na main / implantado / canário técnico / aceite das pilotos / ativação operacional.
5. Dossiê atualizado e publicação confirmada ou pendência nominal.
6. Roteiro de teste e caixa do Founder com ações concretas mínimas.
7. Handoff de encerramento: **próximo assunto é EXTRA-002 investigação Agger, a ser alinhada em nova proposta/chat; não executar agora**. Depois virão canais 099 após pilotos e os auxiliares na sequência planejada.

Comece pelo preflight, RP0 e card. Não me devolva apenas uma análise: valide, converta e execute esta SPEC dentro da autorização descrita, seguindo o AAA até a entrega e a comprovação possível.
