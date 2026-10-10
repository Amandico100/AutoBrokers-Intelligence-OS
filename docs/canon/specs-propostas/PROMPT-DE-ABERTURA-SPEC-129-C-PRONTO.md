# Prompt de abertura — SPEC-129-C · Mais ramos do Agger (Condomínio → Residencial → Empresarial)

> Preparado em 10/10/2026 pelo gerente da SPEC-133-A.1. Abre num chat NOVO (D-133A1-06: o chat anterior chegou ao teto de contexto).
> Copie o bloco abaixo inteiro.

```
Execute a SPEC-129-C (mais ramos do Agger: Condomínio, Residencial e Empresarial, nesta ordem) na pasta AutoBrokers-FIX, no rito AAA
v13 (protocolo §0–§3), decidindo pela maior nota, sem parar para perguntar, e me traga o relatório completo no fim (CLAUDE.md §12.2).

Leia antes, nesta ordem: CLAUDE.md · docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md · docs/canon/GLOSSARIO.md ·
docs/canon/programa-multicalculo/ESTADO-DO-PROGRAMA.md · PLANO-MESTRE-MULTICALCULO.md (a 129-C e o acréscimo de 10/10) ·
A-PROVA-DO-AGGER.md §10 (os ramos, os códigos, os formulários medidos: Condomínio 83 campos/43 obrigatórios, Residencial 86/33,
Empresarial 59/16; fixture backend/tests/fixtures/agger_formularios/formularios_por_ramo.json) e §11 (as contas dedicadas do robô) ·
RETORNO-DO-FOUNDER-2026-10-10.md (a parte da 129-C, palavra por palavra) · SITUACOES-DE-ENTRADA-DA-COTACAO.md ·
docs/canon/specs-propostas/SPEC-131-0-CONTAS-COMERCIAIS-E-CONEXOES.md (o que NÃO é desta SPEC: comerciais, Aggers por pessoa).

O que o Founder decidiu (10/10):
- a ordem: Condomínio, Residencial, Empresarial (auto já existe; no futuro, todos os ramos);
- o mesmo motor e o mesmo montador da 129-B, um pedido e um preset por ramo — nunca motor novo (D-MC-73, CLAUDE.md §5);
- as coberturas de cada ramo vêm das APÓLICES reais: você está AUTORIZADO a baixar até 15 apólices de cada ramo pela InfoCap da
  Resulta (conectada na corretora fictícia AMANDUS SEGUROS), achar os clientes pela busca ("CONDOMINIO", "LTDA"…), pelas conversas da
  Saionara (que cuida de residencial, empresarial e condomínio) ou navegando — e guardar as apólices no intake ou no storage, à
  disposição dos próximos chats, sem dado pessoal em arquivo versionado;
- as seguradoras de cada ramo: medir na InfoCap (API) quais seguradoras têm mais apólices por ramo (o Founder acha que o residencial
  é ~90 % Allianz, com Yelum e Porto); e criar a PREFERÊNCIA de seguradoras por ramo por corretora como CONFIGURAÇÃO (cada corretora tem
  as suas parcerias — nada fixo para a Resulta, CLAUDE.md §13.9);
- a regra de renovação "+15 % na cobertura básica de um ano para o outro" entra como CONFIGURAÇÃO por ramo (o manual da Resulta ainda
  vai chegar e atualiza os números depois);
- QCM, Cotação e Renovação têm regras separadas (D-133A1-01): esta SPEC entrega o CÁLCULO por ramo; quem pede (o canal, o chat) usa
  depois.

Agger: use as contas DEDICADAS do robô (cotador@ de cada corretora; ligadas pelo conector "Agger da corretora" no painel — T-135; as
senhas estão com o Founder, nunca em arquivo). Regras do A-PROVA §10: sem goto entre telas; logout no fim; "sessão ativa" → Cancelar e
parar; nunca apagar nada; nunca "Excluir cotação". 📊 A Resulta tem pendências no Agger (T-136: HDI, Mitsui, Tokio) — meça antes de
concluir que uma seguradora "não cota o ramo".
Verba de API: US$ 4 (só se precisar de modelo). Bateria em 2 metades, em worktrees separados.
```
