========================================================================
RESPOSTA AO RELATÓRIO DE AUDITORIA — Cobrador, rodada 1
Cole isto inteiro no chat do Cobrador.
04/08/2026
========================================================================

Relatório aprovado. É trabalho de boa qualidade e vou dizer especificamente
o que foi bom, porque o que foi bom precisa continuar:

  - você conferiu a branch em vez de acreditar no briefing, e o briefing
    estava errado. 📊 Confirmado: feat/spec063-atendimento-canais. O erro
    foi meu.
  - você mediu os 8,4% / 67% em vez de estimar, e documentou o método
  - você recusou extrair a biblioteca antes da segunda seguradora (§9.2)
  - você recusou a tabela de registro no banco com o argumento do §9.1
  - você discordou da ordem com prova, e achou um critério melhor que os dois
  - a §5-bis é observação de quem leu o código de verdade

Continue exatamente assim. Abaixo: acesso destravado, duas correções minhas,
as medições que faltavam, um ponto que precisa subir de gravidade, e as
respostas Q1–Q6.

------------------------------------------------------------------------
1. O SUPABASE — DESTRAVADO
------------------------------------------------------------------------

Não era permissão do banco. O Supabase é um conector MCP autorizado por
OAuth, sessão a sessão. A sua nasceu sem autorização.

O Founder vai digitar /mcp no seu chat e autorizar o Supabase. A partir daí
você roda SELECT normalmente.

⚠️ E porque isso importa: o conector entra com SERVICE ROLE. Você tem poder
de escrita. A trava de "só SELECT" é a instrução, não o banco. Ela continua
valendo integralmente. Nenhum INSERT, UPDATE, DELETE ou DDL nesta rodada nem
na próxima sem aprovação explícita.

Nunca traga PII para o relatório. Telefone mascarado: 5547*****463.

------------------------------------------------------------------------
2. DUAS CORREÇÕES DO BRIEFING QUE EU TE DEI
------------------------------------------------------------------------

2.1 — "📊 4 cobranças reais enviadas em 15/07" ESTÁ ERRADO.

📊 Medido em billing_sent_log, 04/08/2026:

    4 linhas · send_mode = 'test' · doc_sent = true · 15/07 13:04

Foram para o NÚMERO DE TESTE, com o PDF anexado. Nenhum cliente recebeu
nada. A cadeia inteira foi provada de ponta a ponta uma vez, em modo seguro.

Isso é melhor notícia do que "cobrança real" — mas é outra notícia, e você
precisa da notícia certa. §12.1: número que engana é defeito de revisão, e
o defeito era meu.

2.2 — OS 34 needs_human NÃO SÃO O ESTADO ATUAL. SÃO CICATRIZ DA OBRA.

Rodei a sua query, e depois a linha de controle:

📊 A classificação (portal_jobs, allianz_corretor, needs_human):

    stage                          itens  pdfs  buscas_vazias   n
    boletos_nao_baixados             1      0        2         26
    boletos_nao_baixados             1      0        0          2
    inadimplentes_nao_localizado    (sem evidence)              5
    sem_linhas_extraiveis            0     n/a       0          1

    → 28 de 34 (82%) extraíram a lista e falharam SÓ no PDF.
      A sua hipótese 💭 estava certa nesta metade.

📊 A linha de controle — e ela derruba a outra metade:

    janela              jobs   extraiu itens   baixou PDF
    comercial 9h-18h     19         13             0
    fora do horário      15         15             0

    → zero PDF nas DUAS janelas, e a janela comercial tem MAIS jobs.
      A mensagem no código que sugere "reexecutar entre 9h-18h" é hipótese
      que o dado não confirma. Você marcou como 💭 e pediu confirmação —
      foi exatamente o processo funcionando.

📊 E a linha do tempo, que é o achado que muda tudo:

    08/07 12:45–21:18   16 jobs done, require_downloads=FALSE, teto=1
                        → ensaios a seco. NUNCA tentaram baixar.
    08/07–11/07 03:50   34 jobs needs_human
                        → a obra sendo feita. Todos ANTES do conserto.
    11/07 04:12          1 job done · 1 item · 1 PDF · exige=true
                        → primeiro download real
    15/07 13:00          1 job done · 4 itens · 4 PDFs · teto=20
                        → A rodada. A única completa que existe.
    15/07 13:04          4 linhas em billing_sent_log, modo test, com anexo

    Nada depois de 15/07. A rotina está is_active=false desde então.

📊 Dos 18 "done", 16 tinham require_downloads: false.

O número "18 done" lê como "funcionou 18 vezes". A verdade medida é:
FUNCIONOU INTEIRO UMA VEZ.

CONSEQUÊNCIA PARA O SEU PLANO: o Bloco 0 muda de pergunta. Não é mais
"classificar os 34" — já está classificado acima, e eles são história de
julho. A pergunta que sobra, e ela é bem mais desconfortável:

    HOJE AINDA FUNCIONA?

Uma rodada verde, uma vez, três semanas atrás, com a rotina desligada
desde então, não é produto funcionando. É prova de conceito. Antes de
construir a segunda seguradora, prove que a primeira ainda de pé — porque
se ela não estiver, você vai copiar um molde quebrado.

------------------------------------------------------------------------
3. AS OUTRAS MEDIÇÕES QUE VOCÊ LISTOU COMO "NÃO MEDI"
------------------------------------------------------------------------

📊 portal_accounts .... 1 linha, 1 portal_key. Confirmado.
📊 tabela portals ..... 17 portais. HDI, Porto, Yelum e Tokio JÁ ESTÃO
                        cadastrados como portais. Falta só a credencial.
📊 portal_sessions .... 1 linha.
📊 portal_jobs ........ 91 · allianz done 18 / needs_human 34
                             · vidros done 1 / needs_human 33 / failed 5
                        Bate com os dois relatórios canônicos.

Continuam não medidos, e continuam seus:
    - se o telefone está mesmo na tela da Allianz (§5-bis) — exige rodar job
    - se a API da HDI existe — é a primeira coisa do seu Bloco 2, como você
      propôs, e eu concordo

------------------------------------------------------------------------
4. O PONTO QUE PRECISA SUBIR DE GRAVIDADE
------------------------------------------------------------------------

Você classificou o "0711110" como 🟠 D3, "defeito de desenho que só aparece
com volume". 📊 Conferi a linha:

    allianz_corretor.py:3300
    agent_fallback = _digits(params.get("codigo_corretor")
                             or item.get("codigo_corretor")
                             or "0711110") or "0711110"

Isso não é volume. É VAZAMENTO ENTRE CORRETORAS.

Se a AutoFleet conectar a Allianz e o JWT não decodificar o epac-broker, a
cadeia busca clientes no código de corretor DA RESULTA — e devolve a
carteira da Resulta para a AutoFleet. Silenciosamente. A lista vem com cara
de certa.

CLAUDE.md §7 (multi-tenant) e §10(4) (P0/P1 cross-tenant é condição de
parada). Isto é 🔴 BLOCKER, não 🟠. Reclassifique e trate no Bloco 1.

E repare como isso conecta com a resposta do Founder à Q5, mais abaixo. Ele
escreveu, com todas as letras:

    "NAO ESTAMOS FAZENDO ISSO PARA A RESULTA OU PARA A AUTOFLEET. ESTAMOS
     FAZENDO PARA TODAS AS CORRETORAS QUE ASSINAREM A AUTOBROKERS."

O "0711110" é exatamente esse princípio falhando dentro do código. É o
produto acreditando que só existe uma corretora, escrito em uma linha.

------------------------------------------------------------------------
5. O QUE FALTA NO SEU PLANO — UMA COISA SÓ
------------------------------------------------------------------------

Não há TESTE DE ISOLAMENTO ENTRE CORRETORAS em nenhum dos 6 blocos.

CLAUDE.md §7 exige, literal: "teste automático de isolamento com dois
tenants reais". O backend roda com service role — RLS sem policy não protege
nada contra erro de filtro no código. E o "0711110" prova que a preocupação
não é teórica.

Entra no Bloco 1, e o guarda precisa PODER FALHAR (§9.3): dois company_id
diferentes, duas credenciais diferentes, e a prova de que cada varredura só
devolve o que é dela. Um teste em que os dois tenants são iguais não guarda
nada.

------------------------------------------------------------------------
6. AS RESPOSTAS — Q1 A Q6
------------------------------------------------------------------------

Q1 — HDI. CONCORDADO.
     E há um motivo a mais que você não citou: a HDI tem o mesmo perfil de
     login E é a única com portal de desenvolvedor. São dois critérios
     independentes apontando para o mesmo lugar. Isso é mais forte que
     qualquer um dos dois sozinho.

Q2 — O telefone do portal NÃO substitui o da InfoCap. É rede de segurança.

     Resposta do Founder, que ele foi conferir com as atendentes da Resulta:
     na InfoCap o telefone é o WhatsApp PESSOAL e fica atualizado. Nas
     apólices às vezes vai telefone de empresa, número secundário, número
     que não é o principal.

     Três consequências de desenho, e elas são obrigatórias:

     (a) A §5-bis continua valendo e continua valiosa — mas como FALLBACK.
         Vale rodar o job e olhar evidence.inadimplentes[].raw.detail. Se o
         telefone estiver lá, é rede de segurança para quando a InfoCap
         falhar. Não é substituto.

     (b) O campo precisa carregar a ORIGEM. §12.1, corolário: se o nome do
         campo mente sobre o que ele guarda, conserte o campo. Um `phone`
         que às vezes é o WhatsApp pessoal e às vezes é o PABX da empresa
         MENTE. Precisa nascer com phone_source: infocap | portal | manual.

     (c) Cobrança com telefone de origem `portal` NÃO SAI SOZINHA — passa
         por aprovação humana. Mandar aviso de dívida para o telefone da
         empresa do cliente é dano real na relação da corretora com ele, e
         é erro que não se desfaz. O freio aqui não é técnico, é de negócio.

Q3 e Q5 — O Founder tem login e senha de TODOS os portais das duas
     corretoras, e da InfoCap das duas. Ele cadastra sob demanda, portal a
     portal, conforme você pedir.

     Ele perguntou o que fazer: Chrome ou dashboard? A resposta é OS DOIS,
     nesta ordem, e explique isso a ele em cada portal novo:

       1º  no Chrome, na mão, ele mesmo
           · confirma que a conta está viva, sem senha expirada, sem troca
             obrigatória de senha, sem bloqueio
           · é onde ele faz a captura F12 — precisa estar logado de verdade
           · revela CAPTCHA, MFA e seletor de código de corretor

       2º  no dashboard (Personalização → Conectores → Portais)
           · guarda no cofre Fernet para o robô usar
           · a senha é cifrada e nunca volta para a tela

     ⚠️ RISCO QUE NINGUÉM LEVANTOU AINDA, e é seu para investigar: alguns
     portais aceitam UMA SESSÃO POR VEZ. Se o robô logar enquanto a
     atendente da corretora está logada, um dos dois cai. Isso derruba
     gente de verdade, no meio do expediente. Confira portal a portal antes
     de propor qualquer agendamento em horário comercial — e se for o caso,
     a rotina roda de madrugada por necessidade, não por preferência.

     Sobre a InfoCap da AutoFleet: o Founder tentou inserir e deu
     "indisponível no momento" — provavelmente o mesmo 500 já medido. Ele
     vai resolver, mas foi explícito: NÃO PARE POR CAUSA DISSO.

Q4 — Como descobrir se há vários códigos de corretor. Três caminhos, do
     mais barato ao definitivo — passe os três ao Founder:

       1. UM MINUTO, AGORA: logado no portal, olhar o topo da tela. Se
          houver seletor de "Sucursal", "Agente", "Código" ou "Filial" com
          mais de uma opção — são vários. Se for texto fixo, é um.

       2. DE GRAÇA, DURANTE A CAPTURA: o código aparece DENTRO DA URL da
          chamada. Na Allianz é literalmente getCustomersName/0711110. Ele
          não precisa procurar — vai estar no print que ele já vai tirar.

       3. DEFINITIVO: ligar para o gerente de contas da seguradora e
          perguntar quantos códigos a corretora tem. Respondem na hora, e é
          a única fonte que não depende de a tela mostrar.

     E o que importa mais que a resposta: ONDE QUER QUE ESSE CÓDIGO MORE,
     NÃO PODE SER NO CÓDIGO-FONTE. Ele mora em portal_accounts, por
     company_id. É a mesma linha do "0711110" da §4 acima — o mesmo defeito,
     visto de outro ângulo.

Q6 — A opinião do Founder está certa e é o modelo canônico. Ele escreveu:
     problema da plataforma → Portal Admin, aviso para nós. Problema da
     corretora → suporte humano, mesmo canal dos dossiês.

     Confirme para ele que concorda, e acrescente duas coisas:

     (a) O TERCEIRO CASO É O SILÊNCIO, e é o pior dos três. A rotina se
         autodesligar depois de N falhas é justamente o evento que mais
         precisa de aviso, e hoje é o único que ninguém vê. Precisa de
         batimento: "rodou e achou 0 inadimplentes" é notícia; "não rodou"
         é alarme. Os dois têm que ser distinguíveis de fora.

     (b) O AVISO NÃO LEVA PII. Ao suporte humano vai "portal HDI falhou, 12
         clientes afetados" — nunca nome, nunca CPF, nunca telefone. §13.3.

------------------------------------------------------------------------
7. O QUE FAZER AGORA
------------------------------------------------------------------------

Nesta rodada você AINDA NÃO ESCREVE CÓDIGO. Entregue o plano revisado, com:

  1. o Bloco 0 reescrito — a pergunta agora é "a Allianz ainda funciona
     hoje?", não "por que 34 falharam em julho"
  2. o "0711110" reclassificado como 🔴 blocker de cross-tenant
  3. o teste de isolamento de dois tenants dentro do Bloco 1, com um guarda
     que consegue falhar
  4. o phone_source e o freio de aprovação para telefone de origem `portal`
  5. o batimento de silêncio no Bloco 5
  6. a receita de captura F12 da HDI, já adaptada ao portal dela, para o
     Founder seguir ao pé da letra — incluindo onde procurar o seletor de
     código de corretor (Q4, caminho 1)

Quando o plano revisado estiver aprovado, aí sim começa o Bloco 2 — e a
primeira coisa dele é conferir se a API da HDI existe, antes de pedir uma
única captura. Você propôs isso e está certo: custa uma hora e pode
economizar o bloco inteiro.

Uma última coisa, e ela vale mais que qualquer item acima: o Founder deixou
claro que este trabalho não é para a Resulta nem para a AutoFleet. É para
toda corretora que assinar. Sempre que uma decisão sua parecer mais simples
porque só existe uma corretora — essa é a decisão errada. O "0711110" é o
que acontece quando ninguém repara nisso.

========================================================================
