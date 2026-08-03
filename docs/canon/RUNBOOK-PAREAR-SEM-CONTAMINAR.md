# Parear um telefone PESSOAL sem contaminar o acervo

> **03/08/2026.** O Founder tem dois WhatsApps pessoais — conversa de família,
> grupos, dia a dia — e precisa pareá-los para uma prova técnica.
> 📊 Tudo aqui foi medido no código e no banco de produção antes de virar
> instrução.

---

## O que já protege sozinho — e o que NÃO protege

| | Protegido? | Por quê |
|---|---|---|
| **Atlas / `ura_maps`** | ✅ **sim** | `observed_events` tem **allowlist fechada por telefone** — 12 seguradoras. Um número que não casa **nunca** entra. Conversa pessoal não chega no Atlas por caminho nenhum |
| **Grupos** | ✅ **sim** | descartados em **4 pontos independentes**, mais `ignoreGroups` na própria instância |
| **Fotos e áudios** | ✅ **sim** | o orçamento de mídia nasce **fechado**: sem ação humana explícita, nada é baixado nem transcrito |
| **Agente respondendo amigo** | ✅ **hoje sim** | 📊 **nenhuma corretora tem agente de atendimento ligado**. O portão é `is_active` — e ele está desligado em todas |
| **Cartas / RAG** | ❌ **NÃO** | 🔴 é aqui que mora o risco |

### O risco, em uma frase

Conversa que **não** é de seguradora vai para `attendance_transcripts` — e é
dela que o destilador faz carta. 📊 **8.916 cartas publicadas** e **69.150
transcrições**, todas dos últimos 7 dias: a máquina funciona e rodou há pouco.
Ela não está desligada — está **sem comida**.

E o pior: 📊 a curadoria publica `pending_review → published` **sem aprovação
humana**. Uma conversa de família viraria carta consultável.

---

## O interruptor que decide tudo

```
observer_scope = "insurers_only"     nada de não-seguradora é gravado
observer_scope = "insurers_and_clients"   grava conversa de segurado também
```

Só isso. Com `insurers_only`, `client_chat_allowed` recusa tudo que não seja
seguradora, e o destilador não recebe nada — porque nada foi escrito.

> **Antes de 03/08 este interruptor se desfazia sozinho.** O pareamento gravava
> `insurers_and_clients` por atribuição, apagando uma escolha explícita a cada
> re-pareamento. Hoje é `setdefault`: o padrão continua o mesmo, e quem escolheu
> permanece escolhido. E `observer_exclusions`, que só valia para as mensagens
> ao vivo, agora vale também para o **histórico** — que é onde está o volume.

---

## O passo a passo

**Ordem importa.** O histórico só chega **depois** que o telefone lê o QR. A
janela entre criar o pareamento e escanear é onde o escopo se ajusta.

```
1  🧑  Abra o pareamento no painel, para a corretora combinada.
       O QR aparece. NÃO ESCANEIE AINDA.

2  🤖  Eu gravo observer_scope = "insurers_only" naquela integração
       e confirmo lendo de volta. Aviso quando estiver.

3  🧑  Só então escaneie. O histórico chega e passa pela fronteira já fechada.

4  🤖  Confirmo por medição: quantas linhas novas em attendance_transcripts
       (tem de ser ZERO) e quantas em observed_events (só seguradora).
```

Se o passo 2 for pulado, o histórico entra inteiro. **Não dá para desfazer bem:**
apagar depois deixa rastro em fila, cache e contadores.

---

## Onde cada número vai

| Número | Onde parear | Papel |
|---|---|---|
| **Pessoal 1** | Amandus Seguros (corretora de testes) | **envia** a resposta do formulário |
| **Pessoal 2** | outra corretora, ou a mesma | **recebe**, e é por ele que a prova acontece |

**Os dois precisam ser pareados.** Não é preferência: o telefone que recebe
precisa estar ligado ao sistema para que a mensagem seja **lida por máquina**.

> Uma pessoa olhando a tela consegue dizer "apareceu um formulário". Não
> consegue dizer se o `paramsJSON` chegou com as chaves na ordem certa, nem se o
> `version` viajou. É exatamente isso que precisa ser conferido — e o olho não
> confere.

E a mensagem do teste **chega pelo webhook mesmo com `insurers_only`**: o escopo
decide o que é **guardado**, não o que é **entregue**. Leio a prova no log da
API, que é transitório, e nada disso vira acervo.

---

## O que fica sem verificação

💭 `DESTILADOR_TETO_POR_RODADA` em produção — não consegui ler o `.env` do
contêiner. Com `0` o destilador não processa nada. **Não estou contando com
isso:** o `insurers_only` protege antes, no ponto onde a conversa seria escrita.
Duas travas, e a que eu controlo vem primeiro.

📊 Risco residual: se alguém do círculo pessoal usar um número que coincida com
os 12 da `INSURER_REGISTRY` (0800 e comerciais de SP/RJ), essa conversa entra no
Atlas. Improvável, e é o único caminho que contaminaria de forma permanente.
