---
> **Status:** Visual Acceptance Pack — SPEC-061 Bloco C
> **Data:** 27/07/2026 · **Branch:** `feat/spec061-control-plane-full`
---

# Visual Acceptance Pack — Portal Admin

## Para que serve este documento

É o **roteiro de conferência** do Founder. Cada linha é uma coisa para abrir e
olhar, com o que se espera ver e o que significa se estiver diferente.

Ele existe porque a diferença entre "o código está certo" e "a tela funciona"
só se fecha com alguém olhando. Eu provei o contrato dos dois lados — o código
escreve o que deve, o banco aceita o que recebe. O que falta é a passagem pelos
olhos.

**Como usar:** abra cada endereço, compare com a coluna "o que você deve ver" e
marque. Onde divergir, me diga o endereço e o que apareceu.

---

## 1. Navegação — a primeira coisa

| # | Onde | O que você deve ver | Se estiver diferente |
|---|---|---|---|
| 1.1 | Qualquer tela do Admin | **Oito** grupos no menu: Visão geral, Corretoras, Operação, Inteligência, Conexões, Conhecimento, Financeiro, Governança | Mais de oito = alguém acrescentou item sem revisão |
| 1.2 | Menu | Nenhum rótulo repetido | Rótulo repetido = ambiguidade, você acerta por sorte |
| 1.3 | Menu | Nenhuma palavra técnica (RBAC, gateway, payload) | Jargão = a tela foi escrita para quem construiu |
| 1.4 | Clique no título de um grupo | Abre a primeira tela do próprio grupo | Ir para outro assunto = o defeito do CA-013 |
| 1.5 | Barra lateral, acima do menu | Campo "Buscar…" com atalho `Ctrl K` | Ausente = a busca não subiu |

---

## 2. A Home — `/admin`

| # | O que você deve ver | Por que importa |
|---|---|---|
| 2.1 | Título **"Como está hoje"** | O título é a pergunta que a tela responde |
| 2.2 | Uma **frase** no topo, em caixa colorida | É o que se lê primeiro e, muitas vezes, só |
| 2.3 | Se a frase disser "não consegui ler N fontes" | **Isso é correto** — a Home nunca diz "tudo bem" sem ter conseguido olhar |
| 2.4 | "Precisa de decisão" **antes** dos números | Decisão manda; número é contexto |
| 2.5 | Números pequenos, no rodapé | Se voltarem a ser quatro caixas grandes, a hierarquia se perdeu |
| 2.6 | "Ver números detalhados e atalhos" recolhido | Os contadores antigos não sumiram — desceram |

---

## 3. O que precisa de mim — `/admin/inbox`

| # | O que você deve ver |
|---|---|
| 3.1 | Hoje, **2 itens**: um sinal de alta severidade e um trabalho falhado |
| 3.2 | Se aparecer um cartão dizendo "afeta N corretoras e N itens", o agrupamento por causa funcionou |
| 3.3 | "Dispensar" tira da sua caixa — e o item original **continua** onde estava |
| 3.4 | Caixa vazia diz "Nada precisa de você agora" — nunca fica muda |

---

## 4. Trabalhos — `/admin/trabalhos`

| # | O que você deve ver |
|---|---|
| 4.1 | Quatro números no topo: total, parados, com problema, corretoras afetadas |
| 4.2 | Uma frase resumindo ("Precisa de atenção: …" ou "Tudo andou sem precisar de ninguém") |
| 4.3 | Filtros: Todos, Falharam, Em andamento, Esperando decisão, Concluídos |
| 4.4 | Em "Falharam", o botão **"Tentar de novo"** |
| 4.5 | Ao clicar, uma caixa pedindo o **motivo** |

---

## 5. Esperando decisão — `/admin/aprovacoes`

| # | O que você deve ver |
|---|---|
| 5.1 | Hoje, provavelmente **vazio** — "Nenhuma decisão esperando você" |
| 5.2 | Quando houver: da **mais antiga** para a mais recente |
| 5.3 | "Ver o que vai acontecer" abre a prévia da ação |
| 5.4 | Recusar **exige** motivo; aprovar não |

---

## 6. O que o sistema sabe fazer — `/admin/capacidades`

| # | O que você deve ver |
|---|---|
| 6.1 | Aviso no topo **se** houver ferramenta ativa com poder desligado |
| 6.2 | Três abas: o que sabe fazer, como faz, o que tem permissão |
| 6.3 | Na aba "Como ele faz", a coluna traduzida: "altera e não desfaz", "fala com alguém de fora" |
| 6.4 | Link para o diagnóstico por agente |

---

## 7. Quem pode o quê — `/admin/governanca`

| # | O que você deve ver | Se estiver diferente |
|---|---|---|
| 7.1 | **Sem** faixa âmbar | Faixa âmbar = o web não está alcançando a API |
| 7.2 | 1 pessoa com acesso: você, "Dono da plataforma", sem prazo | Vazio = o papel não foi lido |
| 7.3 | Formulário "Dar acesso a alguém" | Ausente = a tela mostra a governança e não deixa governar |
| 7.4 | Ao dar ou retirar acesso: pede o **motivo** | |
| 7.5 | Depois do motivo: pede a **senha** | É o step-up. Se não pedir, a confirmação não está ligada |
| 7.6 | Aba "O que foi feito" | Registro do que você acabou de fazer |

---

## 8. A separação das superfícies — o teste mais importante

Este é o único que mexe com **cliente**. Faça com atenção.

| # | Faça isto | O que deve acontecer |
|---|---|---|
| 8.1 | Abra `/admin/team` | Redireciona para `/dashboard/equipe` |
| 8.2 | Abra `/admin/billing` | Redireciona para `/dashboard/plano` |
| 8.3 | Abra `/admin/agent` | Redireciona para `/dashboard/agente` |
| 8.4 | Abra `/admin/documents` | Redireciona para `/dashboard/documentos` |
| 8.5 | Abra `/admin/conversations` | Redireciona para `/dashboard/conversas` |
| 8.6 | Entre com um usuário de **corretora** | Vai para `/dashboard` e **não consegue** ficar em `/admin` |
| 8.7 | No dashboard da corretora | As telas de equipe, agente, documentos e plano estão lá |

> **Se algum redirecionamento falhar**, me diga qual. É o único ponto onde um
> link antigo de cliente pode quebrar.

---

## 9. Canário nas três corretoras

| Corretora | O que conferir |
|---|---|
| **AMANDUS SEGUROS** | Aparece como corretora **normal** na lista, não em "empresas técnicas". É a sua corretora de ensaio |
| **Resulta Seguros** | Aparece normal; nada mudou para ela |
| **AutoFleet** | Idem |

---

## 10. O que este pack **não** cobre

Sou obrigado a ser exato:

- **Aparência em telas pequenas.** Não testei em celular.
- **Leitores de tela.** A acessibilidade não foi auditada.
- **Volume.** As telas foram vistas com 5 corretoras. Com mil, a lista de
  aprovações e a de trabalhos precisam de paginação — hoje têm teto, não página.
- **O step-up com senha real.** O caminho foi provado com teste; a digitação
  em produção é sua.

---

## 11. Números da entrega

| Métrica | Antes | Depois |
|---|---|---|
| Grupos no primeiro nível do Admin | 15 | **8** |
| Páginas do Admin | 44 | 44 |
| Páginas com link no menu | 24 | **36** |
| Páginas órfãs | 9 declaradas (4 reais) | **0** |
| Páginas no dashboard da corretora | 41 | **46** |
| Rotas de API do Admin | 114 | 124 |
| Casos no gate | 30 | **37** |
