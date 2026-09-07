# Como iniciar a SPEC-EXTRA-001 no Fable

**Pacote preparado em 07/09/2026.** São documentos para o novo executor. Nenhum código ou dado de produção foi alterado na preparação.

## 1. O que baixar

Baixe e extraia o ZIP `AUTOBROKERS-SPEC-EXTRA-001-PACOTE.zip`. Ele contém:

| Arquivo | Para que serve |
|---|---|
| `SPEC-EXTRA-001-operacao-dos-pilotos.md` | Proposta detalhada do produto, escopo, autorização, contratos, gates e fechamento |
| `SPEC-EXTRA-001-operacao-dos-pilotos-RESEARCH-PACK.md` | Evidências do código, fontes, premissas a remedir e pesquisa externa |
| `PROMPT-DE-ABERTURA-EXTRA-001-PREENCHIDO.md` | Texto inteiro para colar no novo chat Fable |
| `LEIA-ME-EXTRA-001.md` | Este guia |
| `MANIFESTO-SHA256.txt` | Conferência de integridade pelo executor |

**Use os arquivos originais em Markdown.** Eles são editáveis, podem ser lidos diretamente pelo Claude Code e permitem instalar os documentos no padrão do canon. Não é necessário converter para PDF ou Word.

## 2. Onde colocar

Extraia o pacote em uma pasta local privada, por exemplo uma pasta de entrada fora do repositório. Proposta e prompt contêm os dois telefones de teste que você autorizou; **não faça commit desses arquivos originais em um repositório público**.

Abra o Claude Code na árvore do projeto:

```text
C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX
```

O Fable deve confirmar que é a árvore atualizada. Você pode anexar os arquivos no chat ou informar o caminho absoluto da pasta extraída. O próprio prompt manda conferir os arquivos e instalar cópias sanitizadas no canon. Não precisa mover arquivos manualmente entre as pastas de SPECS.

## 3. O que colar

Abra um **chat novo com o Fable** e cole **todo o conteúdo** de:

`PROMPT-DE-ABERTURA-EXTRA-001-PREENCHIDO.md`

Anexe o pacote ou os arquivos, ou acrescente uma linha informando onde a pasta extraída está na sua máquina. Não cole o prompt antigo da SPEC-099 junto: ele contém a fila anterior e instruções históricas que podem confundir o executor.

## 4. O que o Fable deve fazer sozinho

1. Conferir árvore, revisão e integridade dos arquivos.
2. Medir o estado atual do código e dos contratos necessários.
3. Converter a proposta em SPEC definitiva no canon.
4. Fazer aquecimento e emendas sob o AAA.
5. Implementar cobrança humana/direta, respostas, dedup, avisos e convivência com atendimento.
6. Executar provas e canário nos seus números autorizados, sem tocar nas linhas operacionais das corretoras.
7. Atualizar relatório, índice, fila e dossiê durante a execução.
8. Entregar código gateado e os passos de implantação conforme as permissões do projeto, comprovando o que estiver efetivamente no ar.

Você não precisa decidir novamente email, Meta, segundo WhatsApp ou Agger para ele começar esta SPEC. Essas frentes estão expressamente fora do escopo atual.

## 5. Quando ele pode precisar de você

- Se nenhum dos seus dois números de teste estiver disponível em conexão adequada, pode ser necessário você parear um deles. Ele deve conferir antes de pedir e não pode derrubar sessão operacional.
- Para responder às mensagens do canário, se for necessária interação real de um telefone com o outro.
- Para clicar em Implantar, se esse for o procedimento de autoridade mantido no projeto. Ele deve entregar a ordem e os passos exatos.
- Para conduzir a validação funcional com Saionara e Regina. Seus números operacionais continuam fora da autorização.

Falta de uma dessas ações não deve impedir as tarefas independentes. Mas o executor também não pode dizer que validou algo que depende dela.

## 6. Como acompanhar

O prompt exige manutenção deste dossiê:

https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868

O Fable deve atualizar a fonte `docs/canon/reports/dossies/dossies-autobrokers.html`, acrescentar a EXTRA-001, preservar as demais SPECS e republicar quando tiver a ferramenta/acesso. Se não conseguir publicar o link, deve avisar explicitamente e fornecer o HTML atualizado; salvar o arquivo no GitHub não atualiza automaticamente o artifact do Claude.

No acompanhamento, procure estes marcos separados:

| Marco | O que significa |
|---|---|
| SPEC convertida | Plano validado pelo executor, ainda não é código pronto |
| Implementado e aprovado nos gates | Código e testes concluídos no escopo |
| Na main | Código entregue ao repositório |
| Implantado | Versão confirmada no ambiente |
| Canário aprovado | Fluxo comprovado nos seus números de teste |
| Validado pelas atendentes | Feedback real de Saionara e Regina recebido |

Não aceite “tudo pronto” se o envio direto continuar só com um aviso, se o texto continuar marcado como teste no modo real, se o PDF puder falhar sem alerta, ou se os gates materiais estiverem pendentes sem explicação.

## 7. O que não executar neste novo chat

Não iniciar 099–114, Agger, Meta oficial, email, novos auxiliares ou mudança de Evolution Go. Não usar linha operacional da Resulta/AutoFleet nem enviar a clientes/seguradoras. Não é necessário confirmar novamente o uso dos dois números de teste já autorizados; o executor só deve pedir algo adicional se faltar uma ação concreta indispensável.

Depois que a EXTRA-001 estiver em andamento, volte ao chat de planejamento para preparar a investigação Agger. O handoff orienta o Fable a encerrar esta sessão com o estado real e o próximo assunto, sem inventar ou executar a próxima proposta.

## 8. Diferença entre proposta e SPEC definitiva

Este pacote é uma proposta fundamentada com critérios de aceite. A SPEC definitiva será produzida pelo Fable depois de medir o estado atual. Ele pode corrigir premissas e escolher implementação coerente com o projeto; não pode retirar silenciosamente os resultados exigidos ou ampliar a autorização de testes.

Os hashes são conferidos antes de qualquer sanitização. As cópias canônicas devem manter os aliases TESTE-A/TESTE-B e referenciar a configuração privada. Telefones completos e credenciais não entram no dossiê público.
