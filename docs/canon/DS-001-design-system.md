# DS-001 — Design System do AutoBrokers.ai

Status: canônico ativo  
Owner: AutoBrokers.ai Architect  
Última atualização: 2026-06-06

---

## 1. Objetivo

Este documento define as regras visuais e de experiência para o AutoBrokers.ai.

O objetivo não é criar uma identidade visual decorativa. O objetivo é criar um sistema SaaS premium, limpo, rápido, mobile-first e fácil de navegar, inspirado na clareza de ChatGPT/Claude e adaptado ao mercado de seguros.

---

## 2. Referências principais

### 2.1 ChatGPT

Usar como referência para:

- home chat-first;
- sidebar limpa;
- Apps/Connectors;
- biblioteca;
- página de detalhe de conector;
- modal de autorização/permissão;
- densidade visual baixa;
- hierarquia clara.

### 2.2 Claude

Usar como referência para:

- chat;
- projetos;
- rotinas;
- criação guiada;
- campos simples;
- gatilhos;
- conectores;
- permissões;
- navegação sem excesso de cor.

### 2.3 ResultVision antigo

Usar como referência para:

- domínio de seguros;
- seguradoras;
- corredores;
- canais;
- portal;
- fila/casos/conversas;
- atendimento operacional.

Não usar como referência primária de densidade visual da home.

---

## 3. Princípios visuais

### 3.1 Menos superfície, mais intenção

Cada tela deve ter uma intenção principal.

Evitar:

- muitos cards;
- muitos indicadores;
- botões demais;
- menus inchados;
- textos longos em tela operacional;
- tabelas pesadas como padrão.

### 3.2 Dark-first

O produto deve ser dark-first.

Pode haver light mode no futuro, mas não é prioridade.

### 3.3 Cores com parcimônia

A interface deve ser predominantemente neutra:

- preto;
- grafite;
- cinza;
- branco/off-white;
- azul/ciano apenas para ação e destaque;
- amarelo/vermelho/verde apenas para status.

Não usar muitos gradientes, neon ou efeitos futuristas exagerados.

### 3.4 Profissional, não gamer

O produto pode ter sensação moderna e inteligente, mas deve transmitir confiança para corretoras.

Evitar visual de jogo, cyberpunk ou painel de hacker.

---

## 4. Tokens visuais preliminares

> Estes tokens são direção de design. Claude Design pode refiná-los, mas não deve quebrar os princípios.

### 4.1 Fundo

```txt
--bg-app: #050507
--bg-sidebar: #07070A
--bg-surface: #0D0D12
--bg-card: #111116
--bg-elevated: #16161D
```

### 4.2 Texto

```txt
--text-primary: #F4F4F5
--text-secondary: #B4B4BE
--text-muted: #7A7A86
--text-disabled: #555560
```

### 4.3 Bordas

```txt
--border-subtle: #1F1F27
--border-default: #2A2A35
--border-strong: #3A3A48
```

### 4.4 Ação

```txt
--accent-primary: #2F6BFF
--accent-hover: #3F7BFF
--accent-soft: rgba(47, 107, 255, 0.16)
```

### 4.5 Status

```txt
--success: #22C55E
--warning: #EAB308
--danger: #EF4444
--info: #38BDF8
```

---

## 5. Tipografia

Prioridade:

- Inter ou sistema sans-serif para produto;
- evitar fontes muito futuristas no corpo;
- usar peso e espaçamento para hierarquia;
- títulos claros, sem exagero.

Sugestão:

```txt
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

---

## 6. Componentes-mestre

### 6.1 Página chat-first

Estrutura:

```txt
Sidebar
└── Área principal
    ├── centro com logo/nome AutoBrokers
    ├── frase curta
    ├── input principal
    └── 2 atalhos abaixo
```

Regras:

- input é o elemento mais importante;
- nada de dashboard operacional acima do input;
- atalhos discretos;
- visual limpo.

### 6.2 Galeria

Usada para:

- Auxiliares;
- Conectores;
- Seguradoras;
- templates globais;
- bases de conhecimento no futuro.

Estrutura:

```txt
Título
Descrição curta
Busca/filtro
Abas simples
Grid/lista de cards
```

### 6.3 Página de detalhe em camadas

Usada para:

- seguradora;
- conector;
- Auxiliar;
- agente de atendimento;
- corredor.

Estrutura:

```txt
Breadcrumb/voltar
Header do item
Status
Abas internas
Conteúdo da aba
Ação principal
```

### 6.4 Modal de permissão/ação

Usado para:

- conectar app;
- conectar seguradora;
- ativar Auxiliar;
- aprovar execução;
- conceder acesso.

Deve mostrar:

- o que será conectado;
- quais dados serão acessados;
- quais ações poderão ser feitas;
- risco;
- confirmação explícita.

---

## 7. Cards

Cards devem ser simples.

Um card bom contém:

- ícone discreto;
- título;
- descrição curta;
- status se necessário;
- ação clara.

Evitar:

- múltiplos botões por card;
- descrição longa;
- métricas inventadas;
- poluição visual.

---

## 8. Estados de interface

Toda página deve ter:

- loading;
- vazio;
- erro;
- sucesso;
- sem permissão;
- em breve quando necessário.

Mas “em breve” não deve virar desculpa para poluir a sidebar. Módulos futuros devem ficar ocultos até terem valor real.

---

## 9. Mobile

No mobile:

- listas viram cards;
- detalhes ocupam tela inteira;
- ações principais ficam claras;
- navegação deve permitir voltar facilmente;
- preferir bottom sheet/modais simples para ações rápidas;
- usar transição lateral quando possível.

---

## 10. Anti-padrões proibidos

Não fazer:

- home cheia de cards;
- sidebar com dezenas de itens;
- dashboard operacional como primeira tela;
- páginas que misturam configuração, operação e relatório;
- usar cores fortes em tudo;
- criar interfaces “hacker”;
- copiar visual antigo sem limpeza;
- esconder erro técnico com mensagem genérica;
- criar links mortos.

---

## 11. Critérios de sucesso

O design está correto quando:

1. um corretor entende onde clicar sem explicação;
2. a primeira tela parece um copiloto, não um ERP;
3. ações importantes estão a poucos cliques;
4. configuração não contamina operação;
5. mobile parece nativo em fluxo, não uma versão espremida;
6. páginas avançam em camadas como ChatGPT/Claude;
7. a interface passa confiança, não complexidade.
