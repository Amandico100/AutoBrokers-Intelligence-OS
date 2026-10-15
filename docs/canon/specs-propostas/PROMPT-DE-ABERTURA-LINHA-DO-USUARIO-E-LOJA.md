modelo: claude-opus-5-5

# Prompt de abertura — SPEC-131-0-B2 (a linha do usuário, fase 1) → SPEC-139 (a loja de aplicativos)

> Preparado em 14/10/2026 pelo redator das SPECs (delegado pelo gerente da SPEC-132). Abre num chat NOVO, depois do push da 132.
> Copie o bloco abaixo inteiro e cole no chat novo do Claude Code, na pasta AutoBrokers-FIX.

```
Você é o GERENTE (Opus 5.5) de duas SPECs no MESMO chat, nesta ordem: (1) SPEC-131-0-B2 — a linha do usuário, FASE 1
(docs/canon/specs/SPEC-131-0-B2-a-linha-do-usuario.md) → (2) SPEC-139 — a loja de aplicativos
(docs/canon/specs/SPEC-139-a-loja-de-aplicativos.md). Pasta: AutoBrokers-FIX. Rito: AAA v13 (O FIO) — o único em vigor. Decida
pela maior nota, sem parar para perguntar, e pare SÓ por uma das 8 condições do CLAUDE.md §10. No fim de CADA SPEC: relatório no
repositório (template de reports/) + git push com a saída colada; no fim do chat: a resposta final COMPLETA ao Founder (CLAUDE.md §12.2).

LEIA ANTES (o núcleo, inteiro): CLAUDE.md · docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md · docs/canon/GLOSSARIO.md · a SPEC da vez.
Depois, só o que a SPEC citar: docs/canon/programa-multicalculo/ESTADO-DO-PROGRAMA.md §1 · a proposta
docs/canon/specs-propostas/PROPOSTA-A-LINHA-DO-USUARIO-NO-WHATSAPP.md · docs/canon/specs/SPEC-132-C-o-whatsapp-do-corretor.md e
docs/canon/reports/SPEC-132-C-EXECUTION-REPORT.md (o motor do atalho: backend/app/services/atalho/*) · para a 139: a SPEC-131-B, o
relatório dela e docs/canon/programa-multicalculo/131/DESIGN-DO-PADRAO-DE-APLICATIVO.md · MIGRATIONS-AUTHORITY.md antes de qualquer SQL ·
PENDENCIAS.md só por número (P-132C-*, P-132D-01, P-131B-*, P-16).

PREFLIGHT (cole a saída no relatório): git fetch; git rev-list --count HEAD..origin/main (TEM de ser 0) · git rev-list --count
origin/main..HEAD · git branch --show-current; git rev-parse HEAD · git status --short. Uma branch por SPEC, da origin/main:
spec/131-0-B2-a-linha-do-usuario e, depois do push dela, spec/139-a-loja-de-aplicativos.

AS DECISÕES DO FOUNDER (14/10, em docs/canon/FOUNDER-DECISIONS.md — não re-litigue):
- D-132F-01 híbrido: a LINHA DO USUÁRIO é a base; o número central "AutoBrokers" da 132-C fica como reserva (pronto e desligado).
- D-132F-02 a conversa CONSIGO MESMO ("Mensagem para você"), nunca grupo.
- D-132F-03 as capas da loja EM CÓDIGO (SVG/CSS), sem IA de imagem paga; se ele não gostar, manda as dele pelo cover_url.
- D-132F-04 mensagens do SISTEMA ao corretor pelo WhatsApp: prontas e DESLIGADAS por configuração; nada sai sem ele ligar.
- D-132F-05 envio a clientes = FASE 2, com a 135 (teto ≥ 30/dia por linha, a lista completa na SPEC §9). NÃO é desta execução.
- D-132F-06 o chip de teste é o número de teste do Founder; ele pareia lendo o QR com o celular dele.
- D-132F-07 a renovação sem o teto de 12 por noite (já aplicada na 132 — não mexa).
- D-132F-08 KVM2 nos testes, KVM4 antes das pagantes; build do site com swap (T-174) — o build fora do servidor fica para depois.

O TIME: todo subagente é Opus 5.5 e DECLARA o modelo na 1ª linha do que escreve ("modelo: claude-opus-5-5"); builders frescos, um
por fatia, em PARALELO só com arquivos disjuntos (as tabelas das SPECs); juiz ‖ red team frescos, cegos um ao outro, UMA vez; conserto
único; confirmação se houve blocker; na 139 também o JUIZ DE DESIGN com capturas (≥ 90). Todo pacote a subagente carrega §0–§3, §5 e
§7.3 do protocolo. Nenhum subagente muta a árvore de outro (restaura por cópia). Só UM `next build` por vez (8 GB nesta máquina).

SPEC-131-0-B2 · O BLOCO 0 COMEÇA PELO FOUNDER. Antes de qualquer código: monte a instância de MEDIÇÃO e o receptor temporário da
SPEC §2.1 (só campos de roteamento, nunca o texto de outra conversa, nunca serviço de terceiros); gere o QR, salve como imagem no
scratchpad e ABRA na tela do computador; então escreva ao Founder, exatamente assim, e espere a resposta dele:

  "Preciso de 10 minutos seus com o celular do número de teste. É para medir se o AutoBrokers consegue conversar com você na
   conversa 'Mensagem para você'. Nada é enviado a ninguém além de você.
   1. Pegue o celular do número de teste e abra o WhatsApp.
   2. Android: toque nos três pontinhos no alto, à direita → Aparelhos conectados. iPhone: Configurações (embaixo, à direita) →
      Aparelhos conectados.
   3. Toque em 'Conectar um aparelho' e desbloqueie o celular (digital, rosto ou senha).
   4. Aponte a câmera para o código quadrado que abri na tela do computador. Ele muda sozinho a cada uns 20 segundos; se não ler,
      escreva aqui 'QR de novo'.
      Esperado: em poucos segundos o celular mostra um aparelho novo na lista de Aparelhos conectados. Pode aparecer 'Sincronizando
      mensagens' — é normal; essas mensagens NÃO são guardadas.
   5. Volte às conversas e abra a sua própria conversa: ela aparece com o SEU nome e '(você)' — ou toque no ícone de nova conversa e
      escolha o primeiro contato, 'Mensagem para você'.
   6. Mande ali, uma de cada vez: 'teste 1' · um áudio de uns 5 segundos · uma foto qualquer.
   7. Eu vou responder nessa conversa com uma mensagem que começa com '▸ AutoBrokers'. Me diga aqui: a resposta apareceu? o celular
      tocou ou mostrou aviso (com a tela bloqueada)?
   8. Por fim, mande ou receba uma mensagem qualquer em OUTRA conversa sua. Eu só confiro que ela foi descartada sem ser lida.
   Se der errado: 'Não foi possível conectar' → confira a internet do celular e peça 'QR de novo'; 'limite de aparelhos' → em
   Aparelhos conectados, desconecte um que você não usa e tente de novo.
   No fim eu desconecto o aparelho de medição; se quiser conferir, ele some da lista de Aparelhos conectados."

Com a resposta, feche as premissas M1–M6 da SPEC e aplique a coluna "o que muda". M1 negativa (a mensagem não chega ao webhook) NÃO é
parada: a fase 1 passa a usar o número central da 132-C (D-132F-01) e você registra a decisão com nota. M5 sem como apagar o que o
Evolution GO guarda É parada (CLAUDE.md §10, item 4). Não escreva o número de teste em nenhum arquivo, log, teste ou commit.

SPEC-139 · no BLOCO 0, publique a PRANCHA das capas (3 direções × 4 aplicativos × claro/escuro; SPEC §3) como página privada e mande
o link ao Founder com a pergunta "Qual direção: A, B ou C?". Não espere parado: as fatias L2–L5 não dependem da capa. Se a L1 chegar à
produção das 19 sem resposta, vá com a de maior nota e registre.

GATES de cada SPEC (as tabelas "A régua"): O FIO primeiro e vermelho · mutações vermelhas uma vez · duas corretoras reais · CLAUDE.md
§9.1 completo (rotas montam + next build + next start + requisição) · tsc · bateria em partes (worktrees separados, nunca junction) com
triagem contra reports/BATERIA-LINHA-DE-BASE.txt. Migrations: APPLY/VERIFY/ROLLBACK escritos antes, aplicadas por você (psycopg,
transação, lock_timeout 5s, nunca SET SESSION no pooler). Verba de API do produto: ≤ US$ 0,30 na 131-0-B2, US$ 0 na 139.

ENTREGA: cada SPEC termina com o relatório, as pendências novas em PENDENCIAS.md, as decisões novas em FOUNDER-DECISIONS.md, o
ESTADO-DO-PROGRAMA atualizado, as tarefas novas do Founder em TAREFAS-DO-FOUNDER.md (T-178 em diante; a T-175 é o chip e a T-177 é a direção das capas), git push origin HEAD:main
depois do gate, com a saída colada. A resposta final ao Founder segue o CLAUDE.md §12.2 inteiro: o que mudou para o corretor, o que
ele faz agora (com comando pronto e o que esperar na tela — inclusive o Implantar, lembrando que o smith-web só fora do horário de
atendimento e depois da T-174), se der errado, as decisões com nota, o que ficou fora, e o texto pronto da próxima SPEC (8.2 vida e
moto, ou a 133-B, conforme o ESTADO).
```
