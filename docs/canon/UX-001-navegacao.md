# UX-001 — Arquitetura de Navegação

Status: canônico ativo  
Owner: AutoBrokers.ai Architect  
Última atualização: 2026-06-06

---

## 1. Decisão principal

A experiência da corretora no AutoBrokers.ai será **chat-first, mobile-first e modular em camadas**.

A primeira tela do usuário da corretora é o chat do **AutoBrokers**.

Não deve existir uma home tradicional cheia de cards, métricas ou blocos operacionais como primeira impressão.

---

## 2. Página inicial do dashboard da corretora

Rota principal:

```txt
/dashboard
```

Comportamento esperado:

- renderiza a experiência de chat principal;
- é equivalente ao novo chat do AutoBrokers;
- deve ser limpa, parecida com ChatGPT/Claude;
- deve ter a saudação central;
- deve ter input principal;
- deve ter no máximo dois atalhos abaixo do input.

Atalhos P0:

```txt
Ver atendimentos
Novo auxiliar
```

Regras:

- não criar cards grandes;
- não criar dashboard operacional como primeira tela;
- não mostrar métricas complexas na home;
- não inventar módulos futuros como se estivessem prontos;
- não usar Home da corretora como conceito separado.

---

## 3. Sidebar tenant — visão P0

A sidebar inicial deve ser enxuta.

```txt
INÍCIO
- AutoBrokers

OPERAÇÃO
- Atendimentos

AUTOMAÇÃO
- Auxiliares

PERSONALIZAÇÃO
- Personalizar
```

Pode haver subitens dentro das páginas, mas não todos expostos no primeiro nível.

---

## 4. Sidebar tenant — visão por fases

### Fase 1 — limpa e vendável

```txt
INÍCIO
- AutoBrokers

OPERAÇÃO
- Atendimentos

AUTOMAÇÃO
- Auxiliares

PERSONALIZAÇÃO
- Personalizar
```

### Fase 2 — expansão controlada

Dentro de Atendimentos:

```txt
- Painel
- Fila de atendimentos
- Casos
- Conversas
- Ligações
- Segurados
```

Dentro de Auxiliares:

```txt
- Meus Auxiliares
- Galeria
- Execuções
```

Dentro de Personalizar:

```txt
- Corretora
- Equipe
- Agentes de atendimento
- Seguradoras e canais
- Conectores
- Conhecimento
- Custos IA
```

### Fase 3 — navegação avançada

Apenas depois de validação real:

```txt
- Relatórios
- Logs
- Auditoria
- Billing
- Vault avançado
- Catálogo global customizado
```

---

## 5. Regra de ouro da navegação

Não colocar tudo na sidebar.

O padrão correto é:

```txt
Sidebar enxuta → página índice limpa → detalhe em camadas → modal de permissão/ação
```

Referências de comportamento:

- ChatGPT Apps: lista/galeria → detalhe → conectar;
- Claude Routines: lista/criar → configuração → gatilho/conectores/permissões;
- ResultVision: seguradora → abas → corredores/canais/portal.

---

## 6. Padrão de navegação em camadas

O usuário deve avançar progressivamente:

```txt
Módulo → item → detalhe → configuração/ação
```

Exemplo em Seguradoras:

```txt
Personalizar → Seguradoras → Allianz → Canais → Corredor Residencial → Configurar
```

Exemplo em Auxiliares:

```txt
Auxiliares → Galeria → Cobrança de documentos → Personalizar → Ativar
```

Exemplo em Conectores:

```txt
Personalizar → Conectores → Google Drive → Permissões → Conectar
```

---

## 7. Mobile-first

No mobile, a experiência deve parecer que o usuário avança para uma nova camada.

Comportamento desejado:

- sidebar vira menu compacto;
- páginas de detalhe ocupam a tela;
- transição lateral rápida ao entrar em detalhe;
- breadcrumb simples ou botão voltar;
- nada de tabelas largas como interface principal;
- cards e listas substituem tabelas sempre que possível.

---

## 8. Separação entre operação e configuração

### Operação

Onde o usuário trabalha no dia a dia.

Inclui:

- AutoBrokers;
- Atendimentos;
- Auxiliares;
- Execuções;
- conversas;
- casos;
- pendências.

### Configuração/Personalização

Onde o usuário prepara o sistema.

Inclui:

- corretora;
- usuários;
- agentes;
- seguradoras;
- corredores;
- conectores;
- conhecimento;
- permissões;
- custos.

Regra:

> Se é algo que o usuário faz todo dia, fica em Operação. Se é algo que ele ajusta para o sistema funcionar, fica em Personalizar.

---

## 9. Admin Global

O Admin Global é separado do dashboard da corretora.

Apenas equipe interna AutoBrokers.ai acessa.

Responsabilidades:

- corretoras/tenants;
- planos;
- créditos;
- usuários globais;
- modelos LLM;
- tabela de custos;
- templates globais;
- Auxiliares globais;
- catálogo global;
- conectores globais;
- logs;
- auditoria;
- governança.

Não misturar Admin Global com experiência do tenant.

---

## 10. Itens removidos/reprovados

Não usar:

- página Estudos;
- Conversa ao vivo antiga;
- Home da corretora criada no batch 35D;
- dashboard operacional como primeira tela;
- sidebar com 30 itens expostos;
- cards operacionais na página inicial;
- nomes JARVYS/Smith visíveis.

---

## 11. Critérios de sucesso

A arquitetura de navegação está correta quando:

1. usuário entra e vê AutoBrokers como primeira experiência;
2. consegue acessar Atendimento e Auxiliares sem confusão;
3. configuração fica agrupada em Personalizar;
4. mobile não parece uma versão espremida do desktop;
5. não há links mortos;
6. módulos futuros aparecem apenas quando houver base real.
