# BioGate AI

BioGate AI is a biometric authentication SaaS built with Python, FastAPI, computer vision, voice verification, dynamic phrase validation, risk scoring, audit logs, and security dashboards.

O projeto foi desenhado para parecer e evoluir como produto real: autenticação multimodal, camadas de confiança, trilha de auditoria, LGPD, análise de risco e uma experiência visual inspirada em mission control.

## Visão do Produto

BioGate AI não pergunta apenas se a senha está correta. Ele pergunta:

```txt
Essa tentativa realmente parece pertencer ao usuário?
```

Para responder isso, o sistema combina:

```txt
senha ou código
+ rosto
+ voz
+ frase dinâmica
+ contexto do dispositivo
+ histórico de tentativas
+ score de risco
```

## O Que o Projeto É

- Uma plataforma SaaS de autenticação biométrica multimodal
- Um produto de segurança com trilha de auditoria
- Um sistema de score de confiança e risco contextual
- Um projeto de portfólio forte em backend, IA aplicada e arquitetura

## O Que o Projeto Não É

- Pseudociência
- Leitor de mente
- Detector absoluto de emoção
- Sistema invasivo sem consentimento

As partes de "auto-conhecimento", "padrões ocultos" e "intervenção" devem ser implementadas de forma tecnicamente defensável: análise comportamental de acesso, explicabilidade de risco, recomendação de segurança e UX adaptativa, nunca promessas biomédicas irreais.

## Proposta de Valor

BioGate AI entrega uma cadeia de confiança composta por múltiplos sinais:

```txt
Credenciais
-> Biometria facial
-> Verificação de voz
-> Frase dinâmica
-> Sinais de contexto
-> Decisão explicável
-> Auditoria completa
```

Isso permite:

- Reduzir fraudes simples baseadas apenas em senha
- Tornar o login mais auditável e rastreável
- Detectar tentativas suspeitas com base em múltiplos fatores
- Exigir revalidação quando o contexto parecer anômalo

## Funcionalidades Principais

- Cadastro de usuários e organizações
- Consentimento biométrico alinhado à LGPD
- Registro facial e vocal
- Login com rosto, voz e frase dinâmica
- Score de confiança multimodal
- Risk engine contextual
- Decision engine com aprovação, negação ou análise adicional
- Logs de auditoria e eventos de segurança
- Dashboard administrativo
- WebSocket para feedback em tempo real
- Modo demo sem biometria real

## Fluxo de Cadastro Biométrico

```txt
1. Usuário cria a conta
2. Usuário aceita o consentimento biométrico
3. Frontend abre câmera e microfone
4. Sistema coleta 3 amostras faciais
5. Sistema coleta 3 amostras de voz
6. Backend extrai embeddings e features
7. Dados biométricos são normalizados e agregados
8. Embeddings são criptografados
9. Sistema registra modelo, dispositivo, IP e data
10. Auditoria registra o evento
```

## Fluxo de Login Biométrico

```txt
1. Usuário informa email/senha ou código
2. Sistema valida a primeira camada
3. Sistema gera frase dinâmica
4. Frontend pede acesso a câmera e microfone
5. Usuário olha para a câmera
6. Usuário fala a frase solicitada
7. Backend processa rosto, voz e frase
8. Risk engine calcula risco contextual
9. Decision engine calcula confiança final
10. Sistema aprova, nega ou direciona para revisão
11. Auditoria registra a tentativa
```

## Exemplo de Resposta de Verificação

```json
{
  "face_score": 0.91,
  "voice_score": 0.84,
  "phrase_score": 0.96,
  "liveness_score": 0.81,
  "risk_score": 0.18,
  "final_confidence": 0.89,
  "status": "approved"
}
```

## Arquitetura Conceitual

```txt
Frontend Web
  ↓
API Gateway
  ↓
FastAPI Backend
  ↓
Auth Service
  ↓
Biometric Service
  ├── Face Engine
  ├── Voice Engine
  ├── Phrase Engine
  └── Liveness Engine
  ↓
Risk Engine
  ↓
Decision Engine
  ↓
PostgreSQL / Redis / Object Storage
  ↓
Audit Dashboard
```

## Módulos do Produto

### 1. Identity Core

- cadastro
- sessão
- JWT
- refresh token
- roles
- multiempresa
- recuperação de acesso
- bloqueio por falhas

### 2. Biometric Core

- captura facial
- extração de embeddings
- captura de voz
- análise acústica
- transcrição de frase
- comparação biométrica
- liveness detection inicial
- anti-spoofing gradual

### 3. Risk Engine

- risco por IP
- risco por dispositivo
- horário e contexto
- falhas anteriores
- mudança de padrão operacional
- score explicável

### 4. Audit Engine

- logs imutáveis
- rastreamento de decisão
- eventos de segurança
- exportação futura
- histórico de tentativas

### 5. Behavioral Intelligence

- padrão de acesso por horário
- anomalias de dispositivo
- anomalias de localização
- deriva gradual de score
- recomendações de segurança

### 6. Intervention Engine

- pedir nova frase
- exigir nova captura
- exigir segundo fator
- bloquear temporariamente
- revogar token
- encaminhar para revisão manual

## Decision Engine

O login não depende de uma única métrica.

```txt
final_confidence =
(face_score * 0.35)
+ (voice_score * 0.25)
+ (phrase_score * 0.20)
+ (liveness_score * 0.10)
+ (context_score * 0.10)
```

Faixas sugeridas:

```txt
>= 0.85 -> aprovado
0.65 a 0.84 -> verificação adicional
< 0.65 -> negado
```

## Eventos de WebSocket

```json
{
  "event": "FACE_ANALYZING",
  "progress": 42,
  "message": "Extraindo embedding facial"
}
```

Eventos planejados:

- `CAPTURE_STARTED`
- `FACE_DETECTED`
- `FACE_ANALYZING`
- `VOICE_RECORDING`
- `VOICE_ANALYZING`
- `PHRASE_TRANSCRIBED`
- `RISK_CALCULATED`
- `DECISION_READY`

## Stack Técnica

### Backend

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery
- Loguru
- Argon2id
- JWT
- OpenCV
- InsightFace ou DeepFace
- librosa
- faster-whisper

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- Shadcn/ui
- Framer Motion
- WebRTC
- MediaRecorder API
- WebSocket
- Recharts

### Infraestrutura

- Docker
- Docker Compose
- GitHub Actions
- S3-compatible storage
- PostgreSQL gerenciado
- Redis gerenciado
- Evolução para Kubernetes e observabilidade

## Estrutura do Repositório

```txt
biogate-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── infrastructure/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── workers/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── public/
│   └── styles/
├── docs/
│   ├── api.md
│   ├── architecture.md
│   ├── biometric-policy.md
│   ├── deployment.md
│   ├── lgpd.md
│   └── security.md
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Design de Interface

Nome visual:

```txt
Mission Control Identity UI
```

Direção estética:

- visual de central de comando
- densidade informacional alta
- painéis operacionais
- contraste técnico
- tipografia mista entre leitura e dados

Paleta-base:

- `#020617` background principal
- `#0F172A` cards
- `#1E293B` bordas
- `#E2E8F0` texto
- `#00FF88` verde operacional
- `#38BDF8` azul técnico
- `#EF4444` vermelho crítico
- `#FACC15` amarelo alerta

## Segurança e Privacidade

Controles obrigatórios:

- Hash de senha com Argon2id
- JWT com expiração curta
- refresh token rotativo
- rate limiting
- bloqueio após falhas consecutivas
- criptografia de embeddings
- consentimento explícito
- exclusão de dados biométricos
- logs de auditoria
- retenção definida por política

Princípios importantes:

- não armazenar imagem facial crua como padrão
- não armazenar áudio bruto sem finalidade e consentimento
- armazenar embeddings sempre que possível
- separar autenticação, auditoria e risco

## LGPD

Dados biométricos são dados pessoais sensíveis. O produto deve oferecer:

- consentimento explícito
- finalidade clara
- revogação de consentimento
- exclusão de dados
- política de retenção
- trilha de acesso
- minimização de dados
- criptografia em repouso e em trânsito

## Estado Atual do Repositório

Esta primeira base do repositório contém:

- documentação principal do produto
- documentação de arquitetura e segurança
- scaffold inicial do backend FastAPI
- configuração inicial de ambiente
- composição local com PostgreSQL e Redis

Ou seja: o projeto já nasce organizado para crescer como produto e não apenas como experimento.

## Roadmap

### MVP

- cadastro de usuário
- login com email e senha
- consentimento biométrico
- captura facial simples
- captura de áudio
- transcrição de frase
- score facial básico
- score de frase
- risk score simples
- logs no PostgreSQL
- dashboard inicial
- modo demo

### Fase Avançada

- voice embedding real
- liveness detection
- anti-spoofing
- Celery
- WebSocket completo
- painel admin
- multiempresa
- exportação CSV e PDF
- alertas por email

### Fase Enterprise

- Kubernetes
- Terraform
- Prometheus
- Grafana
- OpenTelemetry
- tenant isolation
- rotação de chaves
- policy engine
- observabilidade completa

## Execução Local

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload
```

### 2. Docker Compose

```bash
docker compose up --build
```

### 3. Documentação da API

Com o backend rodando:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## GitHub Positioning

Este projeto é excelente para GitHub porque demonstra:

- arquitetura de software
- backend moderno em Python
- segurança aplicada
- biometria realista
- design de produto
- documentação forte
- preocupação com privacidade e conformidade

## Resumo Técnico para README Curto

> BioGate AI is a biometric authentication platform built with FastAPI, computer vision and voice processing. It validates user identity using face recognition, spoken phrase verification and risk scoring, providing secure check-ins with audit logs and confidence dashboards.

## Licença e Próximos Passos

O próximo passo recomendado é implementar o `Identity Core` e o `Biometric Core` em modo demo, conectando o backend FastAPI ao PostgreSQL e ao fluxo de check-in com WebSocket.
