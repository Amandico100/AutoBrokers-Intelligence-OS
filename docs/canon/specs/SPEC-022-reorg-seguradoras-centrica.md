# SPEC-022 — Reorg IA: Personalização Seguradoras-cêntrica

**Autor**: Opus 4.8 (a partir das decisões do founder, 2026-07-06) · **Status**: pronta para execução
**Motivo**: hoje Seguradoras, Portais e Corredores estão espalhados em telas separadas — confuso. O founder quer **centralizar por seguradora**: o corretor escolhe a seguradora e vê/edita TUDO dela num lugar. É aditivo — NÃO contradiz o Fable (que cuida do motor, não da IA das telas).

## Desenho alvo (UX, seguindo o design system; sem gambiarra)
**Personalização → Seguradoras** vira o hub:
- Lista de **cards por seguradora** (Alfa, Allianz, Azul, Bradesco, HDI, MAPFRE, Porto, SURA, Unimed, Sompo, Suhai, SulAmérica, Tokio, Yelum, Zurich…) — cada card com: logo (campo p/ subir depois), nome, e um **status de conexão** (ex.: "Portal conectado" / "Sem credencial" / "N corredores ativos").
- Clicar no card → **página de detalhe da seguradora** (`/dashboard/personalizacao/seguradoras/[insurer_key]`) com **abas**:
  1. **Canais** — os contatos/canais globais da seguradora do jeito que já existe hoje (0800 sinistro/assistência, WhatsApp, vidros…), editáveis. (Reusar o que já está na página Seguradoras atual, filtrado por seguradora.)
  2. **Portais** — os portais daquela seguradora (do registro global `portals`, filtrados por `insurer_key`) + o formulário de **login/senha por corretora** (a UI que já existe em Conectores→Portais, reaproveitada/filtrada). Nota: o **vidros** (abraseuatendimento) é compartilhado por várias — mostrar como card "Vidros (compartilhado)" nas seguradoras que o usam, ou uma seção "Vidros" à parte no hub.
  3. **Corredores** — os corredores (playbooks) daquela seguradora, ativar/pausar (reusar a página Corredores atual, filtrada por seguradora).

## Princípios
- **Reusar componentes existentes** (Canais = a página Seguradoras atual; Portais = a UI de credenciais de Conectores→Portais; Corredores = a página Corredores atual) — só reorganizar a navegação em cards + abas. NADA de duplicar lógica.
- **Atalhos, não mudança de dono**: os cards de Conectores e Corredores continuam existindo; a página da Seguradora só **centraliza atalhos** + embute os formulários. (O founder foi explícito: não trocar de lugar, só centralizar.)
- Endereços de portal/canais = globais (iguais p/ todas); o que muda por corretora é login/senha (já é multi-tenant).
- Design: abas limpas, cards, modal quando fizer sentido — seguir o design system. Sem tudo numa página só.

## Fatias sugeridas (deploy por fatia)
1. Página hub `seguradoras` = lista de cards por seguradora (dados do registro `portals` + `insurer_channels`/`corridors` para o status). 
2. Página detalhe `[insurer_key]` com as 3 abas embutindo/filtrando os componentes existentes.
3. Campo de logo por seguradora (upload) — opcional, depois.

## Regras
- Frontend: `npx tsc --noEmit` antes de commit. `/admin` usa nativos (portais Radix vazam tema); `/dashboard` shadcn ok.
- Sem migração nova provável (reusa `portals`, canais e corredores existentes). Se precisar de um campo (logo_url em `portals`/insurer), expand-only, founder roda.
- NÃO mexer no motor (SPEC-020) nem no cérebro — é só camada de navegação/UX.
