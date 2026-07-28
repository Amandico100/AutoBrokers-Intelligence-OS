---
> **Status:** canônico
> **Versão:** 1.0 · **Criado em:** 27/07/2026
> **Autoridade:** SPEC-062 §30 (backup/DR) e §31 (incidentes)
> **Função:** dizer o que fazer quando algo quebra, antes de estar quebrado
---

# Runbooks — AutoBrokers Intelligence OS

> [!IMPORTANT]
> Este documento é escrito para ser lido **às 23h de um sábado, por alguém com
> pressa**. Frase curta, comando pronto para copiar, e o efeito de cada um
> declarado antes de você rodar.

---

## 1. Inventário real — medido em 27/07/2026

Nada aqui é presumido. Cada número foi lido do sistema no dia.

| Peça | O que guarda | Estado medido | Se perder |
|---|---|---|---|
| **Supabase/Postgres** | tudo que é verdade durável | 168 tabelas, **37 MB**, PG 17.6 | perde-se o produto |
| **MinIO** | documentos e artifacts | bucket `documents`, **18 objetos, 5,28 MB** | perde-se o PDF do segurado |
| **Qdrant** | índice de busca | 3 coleções (2 corretoras + global) | **reconstruível** a partir do Postgres |
| **Redis** | fila, lock, lease, cache | transitório | trabalho em voo se perde; o durável não |
| **Evolution Go** | sessão do WhatsApp | 2 instâncias (Resulta) | re-parear o celular |
| **Vault/env** | segredos | EasyPanel | acesso a tudo para |

**A leitura que importa:** o banco tem 37 MB e o storage 5 MB. Isso é pequeno —
um restore completo é questão de minutos, não de horas. O risco aqui **não é
volume, é ausência de ensaio**: ninguém nunca restaurou nada.

---

## 2. RPO e RTO — propostos, não prometidos

**RPO** = quanto de dado você aceita perder. **RTO** = em quanto tempo você
volta.

| Peça | RPO proposto | RTO proposto | De onde vem |
|---|---|---|---|
| Postgres | 24 h | 2 h | backup diário do plano Supabase |
| MinIO | **1 h** | 2 h | rotina horária para o Backblaze B2 (§6) |
| Qdrant | ∞ (reconstruível) | 4 h | reindexar a partir do Postgres |
| Redis | ~0 min de dado durável | 15 min | subir e deixar reencher |
| Evolution Go | sessão | 30 min | re-parear o celular |

> [!WARNING]
> **Estes números são PROPOSTA, não promessa.** Nenhum foi comprovado por
> ensaio de restauração. Prometer RTO sem nunca ter restaurado é o mesmo que
> prometer SLO sem baseline — o número soa bem e não significa nada.
>
> Vira compromisso depois do primeiro ensaio (§4 abaixo).

### O buraco do MinIO — FECHADO em 28/07/2026

Até esta data, o Supabase fazia backup do Postgres pelo plano e **o MinIO não
tinha rotina nenhuma**. Cada objeto é um documento que a corretora enviou, e o
Postgres guarda o *ponteiro*, não o arquivo — não havia de onde reconstruir.

**O RPO do storage era "desde sempre". Passou a ser 1 hora.** O procedimento de
recuperação e a evidência do primeiro backup estão em **§6 (RB-06)**.

---

## 3. Incidentes — severidade e o que fazer

### Severidade (§31.1)

| Nível | O que é | Exemplo real possível |
|---|---|---|
| **SEV1** | segurado ou corretora afetados **agora** | agente respondendo quando devia estar calado; dado de uma corretora aparecendo em outra |
| **SEV2** | função importante parada | WhatsApp desconectado; Artifact não é gerado |
| **SEV3** | degradação | busca lenta; Atlas atrasado |
| **SEV4** | incômodo | rótulo errado na tela |

**Regra de ouro:** na dúvida entre dois níveis, escolha o **mais grave**.
Rebaixar depois é barato; descobrir tarde não é.

---

### RB-01 · O agente respondeu quando devia estar calado — **SEV1**

**Sintoma:** um segurado recebeu resposta automática com o agente desligado.

**Primeiro, pare o sangramento** (dashboard, 10 segundos):

> Personalização → Corretora → Agente de Atendimento → **Desligar agente**

Se o painel não responder, desligue pelo banco:

```sql
update agents set is_active = false
where company_id = '<ID DA CORRETORA>' and agent_role = 'attendance';
```

**Depois, ache a causa.** Só existem três caminhos possíveis, e o gate
`OBS-02` cobre os três:

```bash
cd backend && python tests/test_observador_silencio.py
python tests/test_orquestracao_pareamento.py
```

Se os dois passarem, o agente estava **legitimamente ligado** — alguém clicou.
Confira `admin_audit_log`.

---

### RB-02 · Dado de uma corretora apareceu em outra — **SEV1**

**Isto não tem tolerância** (§18.3: zero cross-tenant). Não é degradação: é o
fim da confiança.

1. **Anote o caso antes de mexer em qualquer coisa** — qual corretora viu o quê,
   em qual tela, a que horas. Sem isso, a investigação vira memória.
2. Rode os dois gates que cobrem isolamento:
   ```bash
   cd backend
   python tests/test_spec048_isolamento_corretoras.py
   python tests/test_proxy_admin_exige_sessao.py
   ```
3. Se ambos passarem, o vazamento veio de caminho **não coberto** — e essa é a
   informação mais importante do incidente. Registre em `CHANGE-ADDENDA.md`
   como P0 antes de qualquer correção.

---

### RB-03 · Storage fora do ar — **SEV2**

**Sintoma:** nenhum Artifact é gerado; upload de documento falha.

```bash
curl -s https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/health | python -m json.tool
```

Olhe `storage.conectado`. Se for `false`, leia a **dica** que o `/health`
devolve — ela nomeia a causa. As três que já aconteceram:

| Mensagem | Causa | Correção |
|---|---|---|
| `invalid hostname` | underscore no `MINIO_ENDPOINT` | usar o domínio público, `MINIO_SECURE=true` |
| `getaddrinfo failed` | nome não resolve | conferir o serviço no EasyPanel |
| `403` | credencial errada | conferir `MINIO_ROOT_USER` / `PASSWORD` |

---

### RB-04 · WhatsApp caiu — **SEV2**

**Sintoma:** `channel_status` diferente de `connected`.

```bash
curl -s -H "apikey: <EVOLUTION_GO_GLOBAL_KEY>" \
  https://autobrokers-intelligence-os-evolution-go-teste.golhpm.easypanel.host/instance/all
```

Se `connected: false` com `qr_expired`, é só re-parear pelo dashboard.

> [!NOTE]
> **Re-parear é seguro.** Desde 27/07/2026 o pareamento não mexe mais no estado
> do agente de atendimento (D23) — quem estava ligado continua ligado, quem
> estava desligado continua desligado. Antes disso, re-parear silenciava um
> agente em produção.

---

### RB-05 · Uma corretora foi bloqueada sem ninguém decidir — **SEV1**

**Sintoma:** chat sem resposta, auxiliares devolvendo 402.

```bash
cd backend && python tests/test_spec062_porteira_de_cobranca.py
```

Confira as duas variáveis:

```
BILLING_ENFORCEMENT      tem de estar AUSENTE
COMMERCIAL_GO_LIVE_AT    tem de estar AUSENTE
```

Se alguma existir e não houver decisão do Founder registrada em
`FOUNDER-DECISIONS.md`, **remova a variável e faça redeploy.** Foi
exatamente isto que deixou a AutoFleet sem serviço em 26/07.

---

## 4. Ensaio de restauração — o que falta fazer

> [!CAUTION]
> **Nunca foi feito.** Enquanto não for, os RPO/RTO da §2 são estimativa.

O ensaio precisa provar quatro coisas, nesta ordem:

1. **Postgres restaura** — restaurar um backup num projeto Supabase novo e
   conferir a contagem de linhas das tabelas críticas (`companies`, `agents`,
   `work_runs`, `attendance_transcripts`).
2. **MinIO restaura** — a rotina existe desde 28/07 e a restauração de UM
   objeto já foi provada por SHA-256 (§6). Falta provar a restauração
   **completa**: derrubar o bucket num ambiente de teste e reconstruir tudo.
3. **Qdrant reconstrói** — apagar uma coleção de teste e reindexar a partir do
   Postgres. Se não reconstruir, a "reconstruibilidade" era suposição.
4. **Redis some sem levar nada durável junto** — derrubar o Redis e confirmar
   que nenhum Work Run aceito se perdeu (§18.3).

**Quando fazer:** depois que Resulta e AutoFleet estiverem em operação
estável. Ensaiar restauração num sistema vazio prova pouco — é justamente o
dado real que torna o ensaio válido.

---

## 5. O que este documento ainda não cobre

Honestidade sobre os limites, para ninguém confiar demais:

- **Nenhum alerta automático.** Tudo aqui depende de alguém perceber. A §19.4
  pede alerta por SLI, e isso depende do baseline dos sete dias.
- **Nenhum ensaio de carga.** Não se sabe quantas conversas simultâneas o
  sistema aguenta.
- **Nenhum postmortem escrito** — não houve incidente registrado ainda.
- **Rotação de segredo não está descrita** aqui: é procedimento do Founder e
  envolve credencial que este documento nunca deve conter.

---

## 6. RB-06 · Recuperar o storage a partir do backup

**Quando usar:** o volume do MinIO se perdeu, corrompeu, ou um documento foi
apagado por engano.

### O que existe

| | |
|---|---|
| Destino | Backblaze B2, bucket **privado** `autobrokers-minio-backup-prod` |
| Endereço | `s3.us-east-005.backblazeb2.com` |
| Frequência | de hora em hora, incremental |
| Retenção | *Keep all versions* — sobrescrever não apaga o anterior |
| Estrutura | os objetos ficam sob o prefixo `documents/` |

**A rotina NUNCA apaga no destino.** Objeto removido do MinIO **continua** na
cópia. É deliberado: um espelho que replica exclusão é inútil no caso que mais
importa.

### Recuperar UM documento

```python
from minio import Minio
from io import BytesIO

B2 = Minio("s3.us-east-005.backblazeb2.com",
           access_key="<MINIO_BACKUP_S3_ACCESS_KEY_ID>",
           secret_key="<MINIO_BACKUP_S3_SECRET_ACCESS_KEY>", secure=True)
MINIO = Minio("<MINIO_ENDPOINT>", access_key="<MINIO_ROOT_USER>",
              secret_key="<MINIO_ROOT_PASSWORD>", secure=True)

caminho = "04b5cdbc-.../arquivo.pdf"          # sem o prefixo `documents/`
r = B2.get_object("autobrokers-minio-backup-prod", f"documents/{caminho}")
dado = r.read(); r.close(); r.release_conn()
MINIO.put_object("documents", caminho, BytesIO(dado), len(dado))
```

### Recuperar TUDO

```bash
cd backend
python -c "from app.services.backup.minio_backup import conferir; print(conferir())"
```

Isso diz o que falta. A restauração completa é o mesmo laço acima, invertendo
origem e destino.

### Conferir sem restaurar nada

```python
from app.services.backup.minio_backup import conferir, provar_restauracao
print(conferir())              # contagem e tamanho batem?
print(provar_restauracao())    # baixa um objeto e compara byte a byte
```

### Evidência do primeiro backup — 28/07/2026

```
copiados=18  pulados=0  bytes=5,28 MB  em 13,0s

CONFERENCIA
  origem ..: 18 objetos, 5.536.030 bytes
  destino .: 18 objetos, 5.536.030 bytes
  OK  contagem e tamanho batem

RESTAURACAO de '04b5cdbc-.../0ceb7719-9fd4'
  sha256 origem : 88aca42d406eb3aab93d149003cd7924
  sha256 backup : 88aca42d406eb3aab93d149003cd7924
  OK  byte a byte idêntico
```

> **O RPO do storage deixou de ser "desde sempre" e passou a ser 1 hora.**

### Por que Python e não `mc` ou `rclone`

Os dois exigiriam instalar um binário na imagem Docker — dependência nova para
manter, atualizar e depurar quando o backup falhar às três da manhã. A
biblioteca `minio` já está instalada e fala S3 com os dois lados. Verificado
contra o Backblaze antes de escrever a rotina: listar, gravar, ler de volta e
comparar byte a byte.
