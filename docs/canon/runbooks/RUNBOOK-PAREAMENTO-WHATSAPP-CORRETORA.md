# Runbook — pareamento do WhatsApp da corretora

## Objetivo

Vincular o número de trabalho como aparelho companheiro para o Observador
silencioso aprender com seguradoras e atendimentos, sem interromper o uso do
celular e sem ativar respostas automáticas.

WhatsApp Business pode parear normalmente por QR. Algumas contas podem exigir
passkey por decisão server-side do WhatsApp; nesse caso, use o runbook de
passkey indicado pela própria tela.

## Antes de chamar a atendente

O suporte deve confirmar no diagnóstico administrativo:

- Evolution Go saudável e na versão `0.7.2-autobrokers.1`;
- integração `purpose=observer` ainda desconectada ou inexistente;
- uma única réplica do provider;
- conexões Postgres dentro da linha de base;
- API, Web, Redis e webhook disponíveis;
- nenhum pareamento ativo para a mesma corretora e finalidade.

Deixe a tela aberta no botão **Gerar QR code**. Não peça à atendente que instale
nada antes de o WhatsApp efetivamente solicitar passkey.

## Parear

1. Confirme que a empresa selecionada no dashboard é a correta.
2. Abra **Personalização → WhatsApp → Conectar WhatsApp da corretora**.
3. Clique uma única vez em **Gerar QR code**.
4. No celular de trabalho, abra **WhatsApp → Configurações → Dispositivos
   conectados → Conectar dispositivo**.
5. A atendente lê o QR e aguarda a tela mostrar **WhatsApp conectado**.
6. Se houver passkey, siga `RUNBOOK-PASSKEY-WHATSAPP.md`; não gere outro QR
   enquanto a tentativa atual estiver ativa.

O celular e o WhatsApp Web continuam funcionando normalmente. O Observador não
marca mensagens como lidas, não aparece online, não rejeita chamadas e não
possui código de envio.

## Depois de conectar

Verifique:

- integração ativa com `purpose=observer`, `scope=insurers_and_clients` e
  `agent_id=null`;
- agente de atendimento da corretora com `is_active=false`;
- webhook inscrito em `QRCODE`, `HISTORY`, `MESSAGE` e `CONNECTION`;
- heartbeat do Observador na Central de Agentes;
- mensagem de seguradora capturada em `observed_events`;
- conversa direta de cliente permitida capturada em `attendance_transcripts`;
- grupos, status, chamadas e números excluídos não armazenados;
- qualquer mídia registrada primeiro como `pending` e enriquecida depois.

## Expiração, cancelamento e nova tentativa

- QR expirado é terminal e não reinicia sozinho.
- Cancelar encerra apenas a tentativa; não altera o WhatsApp.
- Use **Gerar novo QR** somente depois de um estado terminal.
- Informe ao suporte a referência da tela. Nunca envie QR, token, senha, PIN ou
  passkey.

## Ordem inicial

1. Parear Resulta e observar a estabilidade.
2. Validar o primeiro evento e o modo silencioso.
3. Selecionar AutoFleet e repetir o mesmo fluxo isolado.

O QR e a tentativa de uma corretora nunca podem aparecer para outra.
