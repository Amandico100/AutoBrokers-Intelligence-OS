# ADR-002 — Connection Vault

Status: canônico ativo  
Owner: AutoBrokers.ai Architect  
Última atualização: 2026-06-06

---

## 1. Decisão

O AutoBrokers.ai precisa de uma camada central de conexões reutilizáveis por corretora, chamada neste documento de **Connection Vault**.

O Vault guarda conexões, credenciais, permissões e vínculos com serviços externos.

A conexão deve ser feita uma vez e reutilizada por diferentes módulos.

Exemplo:

```txt
Portal Bradesco conectado uma vez → usado por Atendimento, Auxiliares e AutoBrokers
```

---

## 2. Por que isso é necessário

Sem Vault, cada módulo pediria credenciais próprias:

- Atendimento pediria acesso ao portal;
- Auxiliar pediria o mesmo acesso;
- AutoBrokers pediria o mesmo acesso;
- integrações repetiriam configurações;
- usuário ficaria confuso;
- segurança ficaria fraca.

Com Vault:

- corretora conecta uma vez;
- permissões são controladas;
- módulos reutilizam a conexão;
- ações são auditáveis;
- fica mais fácil aplicar aprovação humana.

---

## 3. Tipos de conexão

### 3.1 Ferramentas SaaS

Exemplos:

- Google Drive;
- Google Calendar;
- Gmail;
- Slack;
- Notion;
- GitHub;
- Supabase;
- Airtable;
- outros MCPs.

### 3.2 Canais de comunicação

Exemplos:

- WhatsApp/Evolution;
- Z-API, se mantida como provider alternativo;
- e-mail;
- telefonia;
- SMS.

### 3.3 Sistemas de gestão de corretora

Exemplos:

- InfoCap/CORP;
- Quiver;
- Segfy;
- Capta;
- sistemas internos de concessionárias.

### 3.4 Portais de seguradora

Exemplos:

- Allianz;
- Bradesco;
- HDI;
- Porto;
- Tokio;
- Yelum;
- AXA.

---

## 4. Relação com Seguradoras e Corredores

Seguradoras e corredores usam conexões do Vault.

Exemplo:

```txt
Seguradora: Allianz
Canal: Portal Allianz
Corredor: Residencial / Assistência
Credencial: conexão Allianz Portal no Vault
Módulos autorizados: Atendimento, Auxiliares
```

O Vault não substitui a tela de Seguradoras. Ele é a camada técnica e de permissão por trás dela.

---

## 5. Relação com Auxiliares

Cada Auxiliar declara conexões necessárias.

Exemplo:

```txt
Auxiliar: Cobrança de documentos pendentes
Precisa: WhatsApp, base de segurados, documentos pendentes
Pode: preparar mensagem
Não pode: enviar sem aprovação humana no MVP
```

---

## 6. Relação com AutoBrokers

AutoBrokers pode consultar o Vault para saber:

- quais conexões existem;
- quais estão ativas;
- quais estão quebradas;
- quais módulos podem usar cada conexão;
- quais aprovações são necessárias.

AutoBrokers não deve expor credenciais.

---

## 7. Permissões

Cada conexão deve ter escopos claros.

Exemplos:

```txt
read_documents
write_documents
send_message
read_policy
open_claim
download_file
view_customer
update_customer
```

No MVP, usar nomes amigáveis na UI:

```txt
Pode ler documentos
Pode preparar mensagens
Pode enviar mensagens com aprovação
Pode consultar portal
```

---

## 8. Aprovação humana

Qualquer ação externa sensível deve exigir aprovação humana no MVP.

A conexão pode existir, mas a permissão de execução real deve ser controlada.

Exemplo:

```txt
Auxiliar prepara mensagem → humano revisa → humano envia/aprova envio
```

---

## 9. UI recomendada

Padrão visual inspirado em ChatGPT Apps/Connectors:

```txt
Personalizar → Conectores
```

Tela:

- busca;
- categorias;
- cards de conexão;
- status;
- página de detalhe;
- modal de permissão;
- botão conectar/desconectar.

Categorias possíveis:

```txt
Seguradoras
Comunicação
Documentos
Calendário
Sistemas da corretora
Produtividade
```

---

## 10. Estados da conexão

Estados mínimos:

```txt
available
connected
needs_attention
expired
blocked
disabled
```

Linguagem visível:

```txt
Disponível
Conectado
Precisa de atenção
Expirado
Bloqueado
Desativado
```

---

## 11. Segurança

Regras:

- credenciais nunca aparecem no client;
- service role não pode ir para bundle público;
- secrets ficam criptografados;
- logs não devem imprimir segredo;
- rotacionar credenciais expostas em sandbox antes de produção;
- toda ação externa deve ser auditável.

---

## 12. Implementação por fases

### P0 — documento e UI fake segura

- documentar Vault;
- mostrar conectores em UI limpa;
- não conectar serviços reais sem backend seguro;
- não executar ação externa real.

### P1 — conexões internas reais

- WhatsApp/Evolution sandbox;
- Google Drive ou Supabase como primeira conexão simples;
- status e logs;
- autorização por tenant.

### P2 — seguradoras e portais

- credenciais de portal;
- status de sessão;
- portal bloqueado/expirado;
- workflows de revalidação;
- integração com corredores.

### P3 — execução avançada

- browser automation;
- n8n workflows;
- ações multi-etapas;
- approvals avançados;
- auditoria completa.

---

## 13. Critérios de sucesso

O Vault estará correto quando:

1. uma conexão puder ser reutilizada por vários módulos;
2. usuário entender o que está conectando;
3. permissões forem claras;
4. credenciais ficarem seguras;
5. ações sensíveis exigirem aprovação;
6. Seguradoras, Auxiliares e AutoBrokers dependerem da mesma fonte de conexão;
7. UI for simples como ChatGPT Apps/Connectors.
