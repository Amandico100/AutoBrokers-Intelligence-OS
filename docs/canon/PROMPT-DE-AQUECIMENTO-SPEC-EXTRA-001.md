# PACOTE · AQUECIMENTO — SPEC-EXTRA-001 · A operação dos pilotos

Você é o EXECUTOR designado da **SPEC-EXTRA-001 · A operação dos pilotos**, em contexto limpo. Modelo:
Opus 5. Antes de executar, sua missão é **provar que a SPEC está errada**. Só depois ela é liberada
(protocolo §5.2). Você não edita a SPEC nem escreve código agora. Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`
(branch `feat/spec-extra-001-operacao-pilotos`, HEAD `34424fa`). Python roda a partir de `backend/`.

## Leia primeiro
```
docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md     §0–§3, §5, §7.3
CLAUDE.md                                   §7 · §9.1 · §9.3 · §12.1
docs/canon/specs/SPEC-EXTRA-001-operacao-dos-pilotos.md   inteira
backend/app/services/billing_collection.py  normalize_billing_config (:398) · _find_whatsapp_integration (:815) · _format_test_message (:888) ·
                                            _already_sent_recibos (:908) · _record_sent (:924) · _send_test_messages (:982) · execute_billing_collection_routine (:1601 até o fim)
backend/app/services/platform_outbound.py   ator_ainda_pode (:842) · send_to_client_guarded (:880) · _entregar_agora (:1071) · check_platform_queue (:1090) · context_note_for (:1182)
backend/app/services/integration_service.py pode_enviar (:233) · get_platform_whatsapp_integration (:258)
backend/app/api/webhook.py                  process_whatsapp_message_background (:370-1000, da linha 1 da função até a chamada da IA)
backend/app/services/atlas/observer_intake.py :790-835
backend/app/services/whatsapp/channel_identity.py inteiro
components/auxiliares/PainelDeRotinas.tsx   :85-125 · :805-860
app/api/dashboard/auxiliaries/cobranca/liberar-reenvio/route.ts
backend/tests/test_o_protocolo_tem_policia.py :60-75
```

## As travas
```
⛔ NENHUMA mensagem sai. NENHUM agente é ligado. NENHUM portal. Banco: só SELECT (use o MCP do Supabase, projeto dcajcvlzcjbmyapmklil, ou leia
   as medições já coladas na SPEC §1 — e diga qual das duas fez).
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token. Telefones só pelos últimos 4 dígitos ou pelos aliases TESTE-A/TESTE-B.
⛔ SOMENTE LEITURA. Você não escreve nada além da resposta (pode rodar testes existentes com `python tests/<arquivo>.py` a partir de backend/).
⛔ A allowlist de canário e a proibição de usar linhas operacionais (AutoFleet …9360; qualquer número fora de TESTE-A/TESTE-B) NÃO são pegadinha.
```

## As perguntas — respondidas com COMANDO e saída, nunca por leitura (§0.4)

1. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador (Fable):** "A rotina `live` já envia o boleto ao segurado; basta expor a opção `live` de volta no seletor da tela." Refute pelo caminho executável atual: da linha 1 de `execute_billing_collection_routine` até o `return`, que chamada envia no ramo `live`?
2. **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador (Fable):** "O índice único `billing_sent_log_uniq`, gravado depois do envio, garante que dois workers nunca enviem a mesma cobrança." Mostre o entrelaçamento (leitura → envio → gravação) que contradiz isso, com as linhas.
3. O modo humano (`equipe`) é semanticamente igual a `approval`? Quem consome hoje uma `approval_requests` com `action_type='send_billing_whatsapp'`? (`grep -rn`.)
4. Uma integração `purpose='observer'` pode alimentar o atendimento? Qual condição realmente decide se o inbound é consumido pelo observador ou segue para o agente? E qual condição decide se a MESMA integração pode ser canal de SAÍDA da cobrança?
5. A SPEC diz que a porta `send_to_client_guarded` hoje exige o agente de atendimento ligado e escolhe a integração sem `para="auxiliar"`. Prove ou refute com as linhas. Se a cobrança chamasse a porta hoje, para uma corretora que só tem o observador ativo, qual seria o `reason` devolvido — e em qual das duas checagens ele cairia primeiro?
6. Liste TODOS os pontos por onde texto, PDF, retorno, alerta ao grupo e fallback de link podem escapar da autorização do canário (isto é, chegar a um número fora da allowlist) no código de HOJE. Para cada um: arquivo:linha e o destino que ele usa.
7. Qual estado a SPEC propõe para "texto aceito e PDF falho"? E para "timeout sem confirmação depois de um efeito possível"? Existe hoje algum estado assim em `billing_sent_log`? (`SELECT` no `information_schema` ou a §1 da SPEC.)
8. Como a SPEC faz a mesma parcela manter identidade entre dois dias, dois runs, modos diferentes (`equipe` → `cliente`) e seguradoras diferentes com o mesmo número de recibo? Há algum caso em que a chave proposta `(company_id, portal_key, recibo) WHERE send_mode='real'` colide indevidamente ou deixa de colidir quando deveria?
9. Por que a atendente receber o pacote não permite concluir que o cliente recebeu? Como a SPEC concilia a passagem `equipe` → `cliente` sem cobrar duas vezes nem esquecer ninguém? O que a rota `liberar` NÃO pode liberar?
10. Como o contexto do caso sobrevive quando muitos outros clientes recebem mensagens (a SPEC cita `context_note_for` com `limit(30)` antes de filtrar o telefone)? Como evita atribuir os casos dos clientes ao número da ATENDENTE no modo `equipe` (a atendente recebe N pacotes; se ela responder, o que o sistema faz)?
11. Como testar atendimento e mudança de assunto ("preciso de guincho") sem ligar o tenant operacional nem abrir chamado na seguradora? Quais flags de produção hoje impedem o acionamento real (cite as linhas que as leem)?
12. Reproduza TRÊS medições da SPEC §1 ao acaso, com comando e resultado sem PII (ex.: contagem de agentes ligados; a chave do índice único; o `reason` de `_entregar_agora` sem integração; a linha 1730-1737).
13. Liste o que você NÃO entendeu ou não conseguiu provar. "Entendi tudo" reprova.
14. Ache um defeito material que a SPEC não aponta — no código atual ou no desenho proposto (ex.: em `registrar_retorno` antes do observador, no claim por `ignore_duplicates`, no `enfileirar=False`, na rota `liberar`). Ou diga onde procurou e não achou.
15. A SPEC decide **não** reenviar segunda via automaticamente a pedido do cliente e **não** ligar o agente da Resulta no canário (fica na caixa do Founder). Dê nota 0–100 a cada uma dessas duas decisões contra a alternativa, com o motivo em uma linha.

## Como responder
- FATO (medi, com o comando) separado de INFERÊNCIA (deduzi).
- Para toda afirmação da forma "A acontece PORQUE B": diga se mediu o ELO (§0.3).
- Sua **nota 0–100 para a SPEC como está**, a lista de EMENDAS (cada uma: seção · o que muda · por quê), e o que a derrubaria de nível.
- O EXECUTION CARD (§0.2) como VOCÊ o preencheria — o orquestrador compara com o dele.
- Responda em português, máximo ~2.500 palavras. Não repita a SPEC; refute-a.
