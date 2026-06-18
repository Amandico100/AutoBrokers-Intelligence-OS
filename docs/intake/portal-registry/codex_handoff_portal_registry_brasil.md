# Handoff consolidado para Codex - Portal Registry de Seguradoras no Brasil

## Objetivo do pacote

Este pacote consolida, em uma versão mais limpa, consistente e pronta para uso, os materiais anexados nesta conversa sobre:

- superfícies digitais operacionais de seguradoras no Brasil para uso por corretoras/corretores;
- camada técnica de integração (APIs, portais de desenvolvedor, catálogos, autenticação e onboarding);
- recomendações práticas para um dashboard SaaS multi-corretora.

O foco foi **não simplificar**, **não inventar URLs**, preservar os critérios de confiança do material original e organizar tudo para que o **Codex** possa consumir o conjunto de forma objetiva.

## Precedência e regras de consolidação

Ao consolidar os anexos, foi adotada a seguinte ordem de precedência:

1. **Registries detalhados linha a linha** dos lotes operacionais anexados.
2. **Resumo operacional amplo** do Prompt 1, usado para seguradoras que não vieram com lote detalhado linha a linha.
3. **Registry técnico detalhado** do Prompt 2 como fonte principal para o bloco técnico.
4. **Resumo técnico** do Prompt 2 para a matriz mestra por seguradora.
5. Quando havia sobreposição entre arquivos operacionais, prevaleceu a versão **mais recente e mais detalhada**.

Regras herdadas do prompt inicial e preservadas neste pacote:

- priorizar fontes oficiais e primárias;
- não inventar URLs;
- separar explicitamente portal do corretor, portal do segurado, terceiro, parceiro e interno quando houver;
- diferenciar `canonical_url` de `launch_url`;
- marcar claramente `confirmed`, `strong_evidence`, `partial_evidence` e, quando aplicável, `inferred`;
- não confundir operação de portal com evidência de API;
- tratar legado e transição de marca de forma explícita;
- manter valores padronizados dos campos estruturados.

## O que este pacote entrega

### Cobertura consolidada

- **Registry operacional detalhado disponível:** 145 linhas, cobrindo 8 seguradoras com detalhe linha a linha.
- **Resumo operacional consolidado:** 18 seguradoras.
- **Registry técnico detalhado:** 44 linhas, cobrindo 15 seguradoras e 3 entidades adjacentes.
- **Base unificada linha a linha:** 189 linhas.
- **Matriz mestra por seguradora:** 19 linhas.

### Inventário dos arquivos finais

| arquivo                                                      |   linhas | descricao                                                                                                    |
|:-------------------------------------------------------------|---------:|:-------------------------------------------------------------------------------------------------------------|
| portal_registry_operacional_detalhado_3lotes_disponiveis.csv |      145 | Registry operacional linha a linha consolidado a partir dos lotes detalhados disponíveis (8 seguradoras).    |
| portal_registry_operacional_resumo_consolidado.csv           |       18 | Resumo operacional por seguradora (18 seguradoras), consolidado do Prompt 1 e overlays dos lotes detalhados. |
| portal_registry_tecnico_detalhado_prompt2_consolidado.csv    |       44 | Registry técnico linha a linha do bloco do Prompt 2 (15 seguradoras + 3 entidades adjacentes).               |
| portal_registry_tecnico_resumo_consolidado.csv               |       15 | Resumo técnico por seguradora (15 seguradoras).                                                              |
| portal_registry_entidades_adjacentes_tecnicas.csv            |        3 | Entidades técnicas adjacentes: Open Insurance Brasil, SUSEP e Junto Seguros.                                 |
| portal_registry_matriz_mestra_por_seguradora.csv             |       19 | Matriz mestra consolidada por seguradora, cruzando bloco operacional e bloco técnico.                        |
| portal_registry_unificado_linha_a_linha.csv                  |      189 | Base unificada linha a linha com metadados de bloco e documento-fonte.                                       |

## Matriz mestra consolidada por seguradora

A tabela abaixo cruza o que já existe de forma operacional e técnica, indicando rapidamente o status de cobertura atual que deve ser usado pelo Codex.

| insurer_name           | coverage_status                               |   operational_rows |   technical_rows | op_dashboard       | tech_dashboard     |
|:-----------------------|:----------------------------------------------|-------------------:|-----------------:|:-------------------|:-------------------|
| Alfa Seguros           | operational_detailed + technical_detailed     |                 12 |                2 | portal_first       | mixed              |
| Allianz                | operational_detailed + technical_detailed     |                 15 |                1 | mixed              | mixed              |
| Azul Seguros           | operational_detailed + technical_detailed     |                 23 |                1 | portal_first       | portal_first       |
| Bradesco Seguros       | operational_summary_only + technical_detailed |                  0 |                4 | mixed              | api_first          |
| Chubb                  | operational_detailed + technical_detailed     |                 14 |                2 | portal_first       | api_first          |
| Generali Brasil        | operational_summary_only                      |                  0 |                0 | portal_first       |                    |
| HDI                    | operational_detailed + technical_detailed     |                 13 |                4 | mixed              | api_first          |
| Liberty                | technical_detailed_only                       |                  0 |                3 |                    | mixed              |
| MAPFRE                 | operational_summary_only + technical_detailed |                  0 |                1 | mixed              | portal_first       |
| Porto                  | operational_detailed + technical_detailed     |                 16 |                4 | mixed              | mixed              |
| Seguros Unimed         | operational_summary_only                      |                  0 |                0 | portal_first       |                    |
| Sompo                  | operational_summary_only + technical_detailed |                  0 |                5 | portal_first       | api_first          |
| Suhai Seguradora       | operational_summary_only                      |                  0 |                0 | portal_first       |                    |
| SulAmérica             | operational_detailed + technical_detailed     |                 36 |                3 | mixed              | api_first          |
| Sura                   | operational_summary_only + technical_detailed |                  0 |                1 | human_only_for_now | human_only_for_now |
| Tokio Marine           | operational_detailed + technical_detailed     |                 16 |                4 | mixed              | mixed              |
| Yelum                  | operational_summary_only + technical_detailed |                  0 |                2 | mixed              | mixed              |
| Yelum (legado Liberty) | operational_summary_only                      |                  0 |                0 | portal_first       |                    |
| Zurich                 | operational_summary_only + technical_detailed |                  0 |                3 | mixed              | mixed              |

## Entidades técnicas adjacentes

Estas entidades não são seguradoras operacionais do registry principal, mas são estratégicas para integração, compliance e padronização.

| insurer_name          | evidencia_tecnica                | jornadas         | dashboard   |
|:----------------------|:---------------------------------|:-----------------|:------------|
| Junto Seguros         | portal de desenvolvedor          | developer_portal | api_first   |
| Open Insurance Brasil | portal de desenvolvedor          | developer_portal | api_first   |
| SUSEP                 | catálogo/API docs + OAuth2/token | api_catalog      | api_first   |

## Como o Codex deve usar este pacote

### Fonte de verdade operacional
O arquivo `portal_registry_operacional_detalhado_3lotes_disponiveis.csv` deve ser tratado como **fonte de verdade linha a linha** para as seguradoras que têm cobertura operacional detalhada no pacote atual.

### Fonte de verdade técnica
O arquivo `portal_registry_tecnico_detalhado_prompt2_consolidado.csv` deve ser tratado como **fonte de verdade linha a linha** para o bloco técnico do Prompt 2.

### Matriz de orquestração por seguradora
O arquivo `portal_registry_matriz_mestra_por_seguradora.csv` é o melhor ponto de entrada para decisão de produto, porque cruza:
- cobertura operacional;
- cobertura técnica;
- risco de bloqueio;
- dependência de onboarding/credencial;
- recomendação de dashboard por seguradora.

### Resumo operacional mais amplo
O arquivo `portal_registry_operacional_resumo_consolidado.csv` amplia a cobertura para seguradoras sem lote detalhado linha a linha nesta rodada. Ele é útil para arquitetura, priorização e backlog, mas **não substitui** o registry operacional detalhado quando este existe.

## Observações importantes de completude

Este pacote está **muito mais completo** do que as versões anteriores porque agora combina:

- lote operacional detalhado para Allianz, Porto, HDI e Tokio Marine;
- lote operacional detalhado para SulAmérica, Azul Seguros, Alfa Seguros e Chubb;
- resumo operacional amplo do Prompt 1 para outras seguradoras relevantes;
- bloco técnico completo do Prompt 2.

Ainda assim, por honestidade metodológica, o pacote distingue claramente dois níveis de cobertura:

- **cobertura operacional detalhada linha a linha**, quando ela realmente existe nos anexos;
- **cobertura operacional resumida por seguradora**, quando o anexo disponível não trouxe o registry operacional linha a linha daquela seguradora.

O Codex deve respeitar essa diferença ao construir automações, prioridades de integração e backlog de aprofundamento.

## Recomendações práticas para o próximo passo no Codex

1. Usar a **matriz mestra** para definir a estratégia por seguradora: `portal_first`, `mixed`, `api_first` ou `human_only_for_now`.
2. Usar o **registry operacional detalhado** para construir deep links, playbooks por jornada e módulos de operação.
3. Usar o **registry técnico detalhado** para mapear integrações futuras, autenticação, sandbox, riscos de bloqueio e governança de credenciais.
4. Tratar as seguradoras com `operational_summary_only + technical_detailed` como candidatas naturais para um próximo lote operacional detalhado.
5. Manter, no produto final, a separação entre:
   - camada operacional;
   - camada técnica;
   - camada de resumo/score por seguradora.

## Gap explícito que o Codex deve conhecer

Para algumas seguradoras, o pacote atual traz:
- **bloco técnico detalhado completo**, e
- **bloco operacional apenas em nível resumido**.

Isso não invalida o material; apenas significa que o próximo aprofundamento operacional, se necessário, deve começar por essas seguradoras já priorizadas pela matriz mestra.

## Conclusão

Este pacote é a melhor consolidação possível com base nos anexos efetivamente fornecidos nesta conversa.  
Ele já está organizado para consumo prático pelo Codex, sem perder as regras de qualidade, confiança, separação de superfícies e governança de fontes que você definiu no prompt inicial.
