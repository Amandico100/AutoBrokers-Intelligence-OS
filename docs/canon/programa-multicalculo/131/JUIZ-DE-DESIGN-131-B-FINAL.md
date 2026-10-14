# JUIZ DE DESIGN FINAL · SPEC-131-B · O aplicativo de Renovação

> Juiz fresco (Opus 5.5, `claude-opus-5-5`) · 13/10/2026 · READ-ONLY · branch `spec/131-B-o-aplicativo` @ `191ecfa` (conserto K3 `c74197d..191ecfa`).
> **V** = visto em captura · **L** = lido no código. As capturas: `scratchpad/design131b/painel2/` (47 PNG + `medidas.jsonl`) e `cliente3/` (16 PNG), com dados sintéticos e `next dev`.
> Abri 16 capturas: loja 390/1440 claro e escuro, Início 390/1440, Renovações lista 390/1440, detalhe 390, Configurar 390, perfil 390/1440, Fila quadro 1440 e lista 390, e cliente celular claro (dobra e inteira), celular escuro sem número e notebook claro (dobra).

## VEREDITO: **91/100**, meta ≥ 90 atingida (era 87)

Os quatro BLOCKERS de design estão fechados e provados em captura. Dos quatro polimentos, três fecharam por inteiro e um quase todo. O que sobra para 95 é acabamento: nada que trave o corretor ou confunda o cliente.

| tela | nota | era | base |
|---|---|---|---|
| A · página do cliente | **93** | 91 | V (4) |
| B1 · loja | **89** | 85 | V (4) |
| B2 · página do aplicativo (cabeçalho e Início) | **90** | 83 | V (3) |
| B3 · Configurar | **91** | 88 | V + L |
| B4 · Renovações (lista, quadro, detalhe) | **91** | 83 | V (3) + medidas 1024/1280/1366 |
| B5 · Meu perfil | **89** | 86 | V (2) + L |
| **geral** (A 35 %, B1–B5 65 %) | **91** | 87 | |

## Os 8 consertos do laudo anterior

| # | conserto | veredito | prova |
|---|---|---|---|
| 1 | os 44 px existirem | **FECHADO** | `tailwind.config.ts:15` estende `minHeight` com a escala de `spacing`. Em `app-configurar_390_claro.png` o 1/2/3 e o Quadro/Lista estão com 44 px. 📊 `medidas.jsonl`: `alvos_abaixo_44: []` em todas as telas do aplicativo nas duas cores. |
| 2 | nome do cliente inteiro na lista | **FECHADO** | `app-renovacoes-lista_1440_claro.png`: "Cliente Exemplo Comprido", "Seguradora Exemplo Norte" e "Pessoa Exemplo" sem "…". O ramo e o responsável foram para a sublinha; a aba vai a `max-w-7xl` (`LarguraDoAplicativo.tsx`). 📊 `cortados: []` em 1024, 1280, 1366 e 1440. |
| 3 | o ícone por cima da capa | **FECHADO** | `app-inicio_390_claro.png`: o ícone aparece inteiro, com anel, sobre a capa. 📊 `tile_visivel_no_topo: true` nas 4 combinações. |
| 4 | uma parcela só no cartão do cliente | **FECHADO** | `cliente3/r_com_dono_celular_light_dobra.png` e `..._notebook_light_dobra.png`: "10x de R$ 554,94" no resumo e no cartão, com total de R$ 5.549. O motivo duplicado saiu (`comparacao.py:857`, `not renovacao`). |
| 5 | "Como começar" no celular | **FECHADO** | `app-inicio_390_claro.png`: o texto ocupa a largura e a ação vai para a linha de baixo ("✓ Conectado · mudar"). |
| 6 | capa grande só no Início | **FECHADO** | Configurar e Renovações abrem com o cabeçalho compacto. 📊 O primeiro cartão da lista sobe de ≈ 780 para **571 px** no celular e fica em **459 px** no notebook (`medidas.jsonl`). |
| 7 | loja sem frase cortada; destaque vivo no claro | **FECHADO** | `loja_1440_claro.png`: as provas quebram em 2 linhas inteiras ("38 renovações calculadas este mês", "Desligado · a configuração fica guardada"), e "Em breve" também, com `line-clamp-2`. O destaque no claro tem cor de verdade: azul à esquerda e violeta no canto. 📊 `prova[*][1] = false` (nenhuma truncada). |
| 8 | perfil e Configurar | **QUASE FECHADO** | O "Conectado" agora é texto escuro com ponto verde (`perfil-conexoes_1440_claro.png`; `AggersDaEquipe.tsx:16`). Não há `confirm()` em `components/vault` (a guarda varre a pasta: `a-loja-e-a-casca.test.mjs:415`). "Pausar" tem ≥ 44 px no celular, e o Avançado ganhou `py-3` (`AbaConfigurar.tsx:317`). **Continua aberto:** o segmentado "Do responsável \| Da corretora" ainda empilha no celular com a pílula do tamanho do texto (`app-configurar_390_claro.png`; `configurar/pecas.tsx:106`). |

## O que se vê de bom agora

- **Loja (B1).** No notebook, uma loja de verdade: destaque com cor, chips com ícone, 4 colunas e provas inteiras.
- **Aplicativo (B2–B4).**
  - O Início no celular tem hierarquia de loja de aplicativo: capa, ícone, nome, selo e botão.
  - A lista do notebook se lê de uma vez: nome, vencimento, seguradora atual → nova, prêmio com ▲/▼ e estado.
  - O detalhe no celular é exemplar: aviso de aumento em frase, hoje × renovação e a barra Enviar / Ver apresentação / Copiar.
- **Cliente (A).**
  - O resumo "hoje × renovação" e "O que mudou" ficam acima da dobra.
  - Os três cartões têm nota e parcela coerente.
  - "Quem cuida de você" e "Pronto para renovar?" fecham com carinho e foco em renovar (DS-001 §5).

## O que falta para 95 (5 itens)

**O corretor ou o cliente notaria:**
1. **O "1 Issue" do Next na tela.**
   - Ele aparece em `app-inicio_1440_claro.png` (canto esquerdo): o modo dev acusou um erro ou aviso no Início.
   - Abrir esse aviso e zerá-lo. O suspeito é o `useSearchParams` sem `<Suspense>` em `components/aplicativos/casca/LarguraDoAplicativo.tsx:14`, novo no K3; outra causa possível é aviso de hidratação.
   - Em produção ele não aparece, mas um aviso de hidratação vira tela piscando.
   - Rodar `next start` + 200 (item 25, que segue **NÃO AVALIADO**).
2. **O segmentado empilhado no Configurar (celular).**
   - Hoje é uma caixa com duas pílulas desalinhadas e um vão à direita (`components/aplicativos/configurar/pecas.tsx:106`).
   - Usar `grid w-full grid-cols-1 sm:inline-flex sm:w-auto`, com cada opção ocupando a largura.
   - É a única tela de Configurar que ainda parece "formulário cru".
3. **Cartões de renovação no celular: cinco botões pretos iguais, inclusive na já "Enviada".**
   - Visto em `app-renovacoes-lista_390_claro.png`, em "Pessoa Exemplo Carvalhos" (`components/aplicativos/renovacao/PecasDaRenovacao.tsx:270`).
   - Se o estado for `enviada`, o botão vira `outline` "Enviar de novo"; o primário fica para quem ainda precisa ser enviado.
   - Assim o olho vai para o que falta.

**Polimento:**

4. **Página do cliente sem número.** O cartão ainda termina num vão vazio onde ficaria o "Quero esta" (`cliente3/r_sem_numero_celular_dark_inteira.png`). Em `backend/app/services/artifacts/proposta_estilo.py:17`, o `margin-top:auto` deve valer só quando há `.want`.
5. **Meu perfil.**
   - No celular, a faixa de abas corta "WhatsApp d…" sem sinal de que rola (`perfil-conexoes_390_claro.png`). A solução é uma esmaecida na borda direita ou rolar a aba ativa para a vista.
   - O link "Personalização → Conectores" mede 38 px (📊 `medidas.jsonl`; `components/perfil/MinhasConexoes.tsx:20`): `inline-flex min-h-[44px] items-center`.
   - No notebook, a faixa de abas segue mais estreita que o cartão.

💭 Projeção do juiz: 1–3 → ≈ 93; 1–5 → ≈ 95.

## Checklist: o que mudou desde o laudo anterior

- **9** (o ícone e o botão sem rolar): FALHA → **OK** (V).
- **16** (contraste AA): FALHA parcial → **OK** (V). O "Conectado" agora é texto `foreground`.
- **24** (a Fila igual após a extração): NÃO AVALIADO → **OK visto** (`fila-quadro_1440_claro.png`, `fila-lista_390_claro.png`). As duas vistas, o contador e a lista do celular estão inteiros. Não há captura "antes" para provar que nada mudou.
  - ⚠️ A Fila mantém o estilo anterior: selos em monoespaçada, "Atualizar" com 34 px e o link "Atendimentos" com 17 px (📊 `medidas.jsonl`).
  - Isso é legado fora da 131-B e não pesou na nota.
- **18** (a barra de salvar) e **25** (`next start` + 200): seguem **NÃO AVALIADOS**.

## Ressalvas das capturas

- ⚠️ `loja_390_claro.png` foi tirada **ainda carregando**: esqueletos e "Ligados (0)". A loja no celular foi julgada pela `loja_390_escuro.png`, que está completa: 1 coluna e provas inteiras. Convém refazer a captura clara com espera pela rede.
- Nas capturas inteiras do cliente no celular, a barra fixa "Tirar uma dúvida | Quero renovar" aparece no meio do cartão. Isso é efeito da captura de página inteira com um elemento fixo, não defeito; na dobra ela fica no rodapé, correta.
- Contraste conferido a olho (o pixel é do laudo anterior); axe/Lighthouse não rodaram.
