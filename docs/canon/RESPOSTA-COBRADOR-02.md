========================================================================
CORREÇÃO AO CHAT DO COBRADOR — rodada 2
Cole isto no chat do Cobrador quando ele voltar com o plano revisado.
05/08/2026
========================================================================

Preciso corrigir uma coisa que te mandei, e ela muda a sua §7.

------------------------------------------------------------------------
1. EU TE DISSE QUE O MATERIAL DE COBRANÇA NÃO EXISTE. ESTAVA ERRADO.
------------------------------------------------------------------------

Na rodada 1 eu escrevi, com base em medição:

    📊 Zero conversas de cobrança pós-boleto em 1.784 conversas destiladas.
       Todos os 27 destiladores relataram, sem exceção.

O número está certo. **A conclusão que tirei dele, não.**

Eu concluí "o material do Auxiliar de Cobrança não está neste canal". A
verdade, que o Founder me contou depois:

    A Saionara, da Resulta, faz a cobrança das DUAS corretoras — Resulta e
    AutoFleet. Elas são do mesmo sócio, com CNPJs diferentes.

📊 As 1.784 conversas que destilamos são **da AutoFleet**. O WhatsApp da
Resulta nunca foi pareado — 📊 a integração de observador dela está
`is_active=false`, `channel_status='retired'`.

**Então o zero não é ausência de material. É ausência de leitura.** A
matéria-prima do Cobrador está inteira no único canal que ninguém abriu.

Isto é o §9.2 do CLAUDE.md me pegando: eu tinha um acervo de UM lado da
operação e tratei o silêncio dele como fato sobre a operação toda. Faltou a
linha de controle — e a linha de controle era justamente a corretora que não
foi medida.

------------------------------------------------------------------------
2. O QUE ISSO MUDA NO SEU PLANO
------------------------------------------------------------------------

**Não muda a ordem das seguradoras.** A HDI continua sendo a primeira, e o
seu argumento do §9.2 (variar um fator só) continua de pé.

**Muda o que você pode esperar de conhecimento.** Você escreveu que o material
de "conversa depois do boleto" é escasso e que o Cobrador não encontraria
matéria-prima. Escreva de novo depois que a Resulta parear: é lá que estão as
perguntas do segurado ao receber o boleto, as objeções, o que a seguradora
aceita depois do vencimento, e o que a corretora não pode resolver.

**E muda a prioridade de uma coisa que estava no fim.** O Bloco 0 do seu plano
esperava acesso ao banco — isso já está resolvido. O que vale esperar agora é
o pareamento da Resulta, porque ele enche o acervo do seu próprio trabalhador.

------------------------------------------------------------------------
3. UM ACHADO QUE VEIO DE GRAÇA E É SEU
------------------------------------------------------------------------

Um destilador encontrou, numa conversa interna da AutoFleet, a única amarra
entre cobrança e sinistro que apareceu em 1.784 conversas:

    📊 Apólice com prêmio pendente TRAVA o sinistro. A Tokio Marine não envia
    nem a relação de documentos do terceiro enquanto houver parcela em aberto.
    A segunda conversa mostra o destrave: "apólice quitada, gentileza enviar
    a relação".

Isso não é conhecimento de cobrança nem de sinistro — é da fronteira, e
nenhum dos dois trabalhadores acharia sozinho. Vale como carta e vale como
argumento de produto: **o Cobrador não recupera só dinheiro, ele destrava
atendimento.**

------------------------------------------------------------------------
4. O ESTADO DO BANCO, PARA VOCÊ NÃO REMEDIR
------------------------------------------------------------------------

📊 Medido em 05/08/2026:

    knowledge_cards ..... 10.818 publicadas · pending_review 0
    portal_accounts ..... 1 linha, 1 portal_key
    tabela portals ...... 17 · HDI, Porto, Yelum e Tokio já cadastrados
    portal_jobs ......... allianz done 18 / needs_human 34
                          vidros  done  1 / needs_human 33 / failed 5
    billing_sent_log .... 4 linhas, send_mode='test', doc_sent=true

E a classificação dos 34 `needs_human`, que você deixou como query pronta:

    28 de 34 extraíram a lista e falharam SÓ no PDF
     5 não acharam a tela
     1 o parser não casou
    todos entre 08 e 11/07 — ANTERIORES à rodada que funcionou

📊 A linha de controle derrubou a hipótese do horário: zero PDF baixado nas
duas janelas, e a janela comercial tem MAIS jobs (19 contra 15).

📊 E o que importa mais: dos 18 `done`, **16 tinham require_downloads: false**
— eram ensaios a seco. O Cobrador funcionou INTEIRO uma vez, em 15/07,
teto 20, 4 itens e 4 PDFs. Nada depois disso.

------------------------------------------------------------------------
5. O QUE EU QUERO DE VOCÊ AGORA
------------------------------------------------------------------------

O plano revisado que pedi na rodada 1, com os seis ajustes — e mais este
sétimo:

  7. reescreva a sua §7.3 ("zero cobrança neste pacote") à luz de que a fonte
     estava fechada, não vazia. Diga o que você espera encontrar quando a
     Resulta parear, e como pretende usar.

Continue sem escrever código. E continue conferindo o que eu te mando: você
já me pegou uma vez na branch errada, e agora eu me peguei numa conclusão
errada. É assim que tem de ser.

========================================================================
