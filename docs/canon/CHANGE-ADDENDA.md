---
> **Status:** canônico — registro append-only
> **Criado em:** 25/07/2026
> **Função:** registrar toda mudança executada além do texto literal de uma SPEC, impedindo alteração silenciosa de escopo
---

# Change Addenda — mudanças além do texto literal das SPECs

## 1. Por que este documento existe

As SPECs 052–062 são detalhadas, mas nenhuma especificação sobrevive intacta ao contato com o código real. O executor **vai** encontrar situações não previstas.

O risco não é a mudança. É a mudança **silenciosa** — aquela que ninguém registrou, ninguém aprovou e que reaparece seis semanas depois como uma divergência inexplicável entre documentação e produção.

```text
Mudança registrada e classificada  → governança
Mudança executada em silêncio      → deriva
```

---

## 2. Regras

1. Este arquivo é **append-only**. Entradas existentes não são editadas nem removidas.
2. Toda alteração além do literal da SPEC recebe entrada aqui **antes ou junto** com o commit que a implementa.
3. Toda entrada é classificada como **BLOCKER**, **ESSENCIAL**, **VALIOSA** ou **FUTURA**.
4. Entradas **BLOCKER** e **ESSENCIAL** podem ser executadas pelo executor dentro da SPEC corrente, desde que registradas.
5. Entradas **VALIOSA** e **FUTURA** são **propostas**. Não são executadas sem decisão em [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md).
6. **Nenhuma entrada pode reduzir escopo.** Redução exige decisão explícita do Founder — ver **D5**.
7. Mudança que altere arquitetura, sequência de SPECs, risco material ou dinheiro **também** vai para `FOUNDER-DECISIONS.md`.
8. Correção de bug dentro do escopo da SPEC **não** vem para cá — vai para o relatório final da SPEC.

---

## 3. Classificação

### BLOCKER
Sem isso, a execução causa erro grave, insegurança, perda de dados, duplicidade estrutural ou inviabilidade técnica.
→ Executar dentro da SPEC corrente. Registrar aqui. Notificar no relatório final.

### ESSENCIAL
Melhora materialmente qualidade, robustez, segurança, experiência ou resultado, e o custo de deixar para depois é maior que o de fazer agora.
→ Executar dentro da SPEC corrente. Registrar aqui.

### VALIOSA
Melhoria real, mas com encaixe natural em uma SPEC posterior ou custo desproporcional agora.
→ **Não executar.** Registrar como proposta.

### FUTURA
Boa ideia que não deve atrasar o lançamento.
→ **Não executar.** Registrar como proposta.

---

## 4. Formato obrigatório de entrada

```markdown
## CA-nnn — <título curto>

**Data:** DD/MM/AAAA · **SPEC:** SPEC-0NN Bloco X · **Classe:** BLOCKER | ESSENCIAL | VALIOSA | FUTURA
**Estado:** EXECUTADA | PROPOSTA | REJEITADA | SUPERSEDED BY CA-nnn

### Problema
O que estava errado ou faltando.

### Evidência
Arquivo:linha, consulta ao banco, saída de teste ou commit. Fato, não impressão.

### Consequência de não fazer
Concreta e específica.

### Mudança
O que foi (ou seria) feito, exatamente.

### Custo e risco
Esforço relativo e risco introduzido.

### Autorização
Executor dentro da SPEC | decisão D-nn do Founder | aguardando decisão.
```

---

## 5. Índice

| ID | Título | SPEC | Classe | Estado | Data |
|---|---|---|---|---|---|
| CA-001 | Cruzamento factual de migrations e checksums iniciais | 054 | ESSENCIAL | EXECUTADA | 25/07/2026 |
| CA-002 | Adiar PPTX e DOCX na SPEC-057 | 057 | VALIOSA | **PROPOSTA — não executar** | 25/07/2026 |
| CA-003 | Adiar SEO/AEO e Business Discovery na SPEC-060 | 060 | VALIOSA | **PROPOSTA — não executar** | 25/07/2026 |
| CA-004 | Simplificar Briefing por cargo na SPEC-059 | 059 | VALIOSA | **PROPOSTA — não executar** | 25/07/2026 |
| CA-005 | Fixar imagens e credenciais do docker-compose | 054 | VALIOSA | PROPOSTA | 25/07/2026 |
| CA-006 | Consolidar os 60 runners em um pack único | 054 | ESSENCIAL | PROPOSTA | 25/07/2026 |
| CA-007 | Substituir testes de inspeção de fonte por testes de comportamento | 054 | ESSENCIAL | PROPOSTA | 25/07/2026 |

---

## CA-001 — Cruzamento factual de migrations e checksums iniciais

**Data:** 25/07/2026 · **SPEC:** SPEC-054 (preparatório, Fase 0) · **Classe:** ESSENCIAL
**Estado:** EXECUTADA

### Problema
A SPEC-054 §8.1 exige baseline reproduzível, mas nem a SPEC nem a auditoria de 24/07 traziam o cruzamento **arquivo × versão aplicada × checksum**. Sem isso, o executor do Bloco B decide no escuro quais arquivos são pendentes e quais já estão em produção.

### Evidência
Cruzamento read-only entre `main` @ `3c8c752` e `supabase_migrations.schema_migrations` (projeto `dcajcvlzcjbmyapmklil`): 21 versões rastreadas, 28 arquivos no repositório, **12** correspondências, **9** versões sem arquivo, **16** arquivos sem versão.

### Consequência de não fazer
Treze arquivos da classe `NÃO RASTREADA` (rotinas, portais, corredores, capability seeds) parecem pendentes e **não são** — as estruturas já existem em produção. Aplicá-los repetiria DDL, sobrescreveria policies e alteraria defaults.

### Mudança
Produzido [`MIGRATIONS-AUTHORITY.md`](MIGRATIONS-AUTHORITY.md) com a classificação completa e o sha256 inicial de cada arquivo, como baseline de integridade do futuro `MANIFEST.md`.

### Custo e risco
Custo baixo — documental. Risco zero: nenhum arquivo foi movido, aplicado ou alterado.

### Autorização
Decisão **D2** do Founder.

---

## CA-002 — Adiar PPTX e DOCX na SPEC-057

**Data:** 25/07/2026 · **SPEC:** SPEC-057 · **Classe:** VALIOSA
**Estado:** **PROPOSTA — NÃO EXECUTAR**

### Problema
A SPEC-057 exige oito formatos de saída. PPTX e DOCX são os de maior custo de implementação e menor contribuição para o efeito "wow" inicial.

### Evidência
SPEC-057 §7.6 e §7.7 · §16.5 e §16.6.

### Consequência de não fazer
Nenhuma imediata. É otimização de cronograma, não correção de defeito.

### Mudança proposta
Entregar web, PDF, XLSX, CSV, gráficos e Evidence Pack no lançamento; PPTX e DOCX logo após.

### Custo e risco
Reduz esforço da SPEC-057. Risco: o Founder pode considerar apresentação executiva parte do wow.

### Autorização
**Rejeitada como execução pela decisão D5.** Permanece registrada. Só muda por nova decisão do Founder.

---

## CA-003 — Adiar SEO/AEO e Business Discovery na SPEC-060

**Data:** 25/07/2026 · **SPEC:** SPEC-060 · **Classe:** VALIOSA
**Estado:** **PROPOSTA — NÃO EXECUTAR**

### Problema
A SPEC-060 inclui auditoria de SEO/AEO (§21) e descoberta de empresas (§19), enquanto o próprio Founder já declarou que Growth e prospecção ficam para uma fase posterior.

### Evidência
SPEC-060 §19 e §21 · SPEC-053 §23 (fora do primeiro ciclo).

### Consequência de não fazer
Nenhuma imediata.

### Mudança proposta
Priorizar `quick`, `verified`, `deep`, `claim_check` e `monitor`; entregar `site_audit` e `business_discovery` em seguida.

### Custo e risco
Reduz esforço. Risco: o Radar de Mercado depende de `monitor`, que **permanece no escopo**.

### Autorização
**Rejeitada como execução pela decisão D5.**

---

## CA-004 — Simplificar Briefing por cargo na SPEC-059

**Data:** 25/07/2026 · **SPEC:** SPEC-059 · **Classe:** VALIOSA
**Estado:** **PROPOSTA — NÃO EXECUTAR**

### Problema
A SPEC-059 §16.6 prevê Briefing personalizado por cargo. Com 5 empresas e poucos usuários, a segmentação por cargo tem pouco sinal para calibrar.

### Evidência
SPEC-059 §16.5 e §16.6 · banco vivo: 5 companies.

### Consequência de não fazer
Nenhuma imediata.

### Mudança proposta
Lançar com Briefing operacional diário + executivo semanal; adicionar segmentação por cargo quando houver volume.

### Custo e risco
Baixo dos dois lados.

### Autorização
**Rejeitada como execução pela decisão D5.**

---

## CA-005 — Fixar imagens e credenciais do docker-compose

**Data:** 25/07/2026 · **SPEC:** SPEC-054 · **Classe:** VALIOSA
**Estado:** PROPOSTA — depende de **P1**

### Problema
`backend/docker-compose.yml` usa `minio/minio:latest` e credenciais `minioadmin/minioadmin123`.

### Evidência
[`backend/docker-compose.yml`](../../backend/docker-compose.yml) · SPEC-053 §25.3 proíbe `latest` em imagem crítica.

### Consequência de não fazer
Se o compose espelhar produção: mudança silenciosa de versão do MinIO e credenciais default expostas. Se for apenas dev local: nenhuma.

### Mudança proposta
Fixar tag do MinIO e mover credenciais para `.env` não versionado.

### Custo e risco
Custo mínimo. **Classificação sobe para ESSENCIAL** se o Founder confirmar que o compose espelha produção — ver P1 secundária 2.

### Autorização
Aguardando resposta de **P1**.

---

## CA-006 — Consolidar os 60 runners em um pack único

**Data:** 25/07/2026 · **SPEC:** SPEC-054 · **Classe:** ESSENCIAL
**Estado:** PROPOSTA — executar no Bloco C da SPEC-054

### Problema
`backend/tests/` contém ~60 arquivos executados isoladamente, sem gate único. Cada SPEC de 054 a 062 referencia um "Broker Outcome Regression Pack" que **não existe** como artefato executável.

### Evidência
`backend/tests/` — 60 arquivos · SPEC-062 §2.1 confirma: *"muitos testes eram runners independentes, e não uma única suíte com gates de release"*.

### Consequência de não fazer
Cada SPEC declara gate verde sem um critério comum. Regressão entre SPECs passa despercebida até a 062.

### Mudança proposta
Criar o pack executável por um comando na SPEC-054 Bloco C, preservando todos os arquivos atuais como casos. Cada SPEC posterior adiciona seus casos ao mesmo pack.

### Custo e risco
Custo médio, uma vez. Risco de não fazer: alto e cumulativo.

### Autorização
Executor dentro da SPEC-054 Bloco C, registrando aqui a mudança de estado para EXECUTADA.

---

## CA-007 — Substituir testes de inspeção de fonte por testes de comportamento

**Data:** 25/07/2026 · **SPEC:** SPEC-054 · **Classe:** ESSENCIAL
**Estado:** PROPOSTA — executar no Bloco B da SPEC-054

### Problema
Testes como `test_spec048_isolamento_corretoras.py` verificam a **presença de um guard no código-fonte**, não seu comportamento em runtime. Passam verde mesmo com o guard quebrado.

### Evidência
[`backend/tests/test_spec048_isolamento_corretoras.py`](../../backend/tests/test_spec048_isolamento_corretoras.py) · auditoria SPEC-054 §12.1.

### Consequência de não fazer
Um gate de isolamento multi-tenant verde que não prova isolamento. É o pior tipo de falso positivo — dá confiança sem dar segurança.

### Mudança proposta
Implementar a suíte real exigida pela SPEC-054 §8.8, executando `anon`, `authenticated` tenant A, `authenticated` tenant B, `service_role` e usuário multiempresa contra o banco. Manter os testes de inspeção como smoke barato, **nunca** como prova de segurança.

### Custo e risco
Custo médio. Risco de não fazer: crítico — é pré-condição para o Gate 2.

### Autorização
Executor dentro da SPEC-054 Bloco B, registrando aqui a mudança de estado para EXECUTADA.

---

## CA-008 — Brand Identity Fabric como pré-requisito do Artifact Hub

**Data:** 25/07/2026 · **Estado:** EXECUTADA (Bloco A) · **SPEC:** 057 · **Origem:** D15

### Lacuna encontrada

A SPEC-057 exige que toda peça saia com a identidade da corretora, mas **nenhum
objeto do sistema guardava identidade de marca**. `companies` tem CNPJ, endereço
e contato — não tem site, logo, cor nem tipografia. O requisito era inexequível
como escrito.

### Mudança

Cinco tabelas novas antes do Artifact Hub: `brand_profiles`, `brand_assets`,
`brand_sources`, `brand_field_provenance`, `brand_profile_versions`. Mais o motor
de cor em `app/services/brand/`.

### Decisão de engenharia que merece registro

**O logo manda na cor, o CSS não.** Medido no primeiro site real testado: o CSS
da Resulta devolve `#f78da7`, `#cf2e2e`, `#ff6900`, `#fcb900` — a paleta padrão
do editor do WordPress, sem uma única cor da marca. O logo devolve `#1D5579`
(94,4% da tinta) e `#EE7501` (5,6%). Ler cor do CSS daria a **toda** corretora
em WordPress a mesma identidade rosa-e-âmbar.

`brand_field_provenance` guarda de onde veio cada campo e com que confiança. Sem
isso, captura automática em material que vai ao cliente final é passivo, não
ativo — o corretor precisa poder conferir e discordar.

### Custo e risco
Custo alto (bloco inteiro). Risco de não fazer: a promessa central da SPEC-057
sairia falsa — peça "personalizada" com a cor da AutoBrokers.

### Autorização
D15.
