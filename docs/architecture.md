# BioGate AI Architecture

## Objetivo

Construir uma plataforma SaaS de autenticação biométrica multimodal com foco em segurança, auditabilidade, escalabilidade gradual e conformidade com LGPD.

## Diretrizes Arquiteturais

- Começar com um MVP realista
- Separar autenticação, biometria, risco e auditoria
- Evitar promessas pseudocientíficas
- Tratar biometria como dado sensível
- Permitir evolução para multiempresa e serviços assíncronos

## Fluxo de Alto Nível

```txt
Frontend Web
  -> API Gateway
  -> FastAPI Backend
  -> Auth Service
  -> Biometric Service
  -> Risk Engine
  -> Decision Engine
  -> Audit Engine
  -> PostgreSQL / Redis / Object Storage
```

## Módulos

### Identity Core

Responsável por:

- contas
- autenticação tradicional
- sessões
- tokens
- papéis e permissões
- bloqueios

### Biometric Core

Responsável por:

- captura e validação de amostras
- extração de embeddings faciais
- features de voz
- transcrição da frase
- comparação de amostras
- score por modalidade

### Risk Engine

Responsável por:

- score contextual
- detecção de dispositivo incomum
- avaliação de histórico
- explicação de risco

### Decision Engine

Responsável por:

- combinar scores
- aplicar regras
- aprovar
- negar
- exigir verificação adicional

### Audit Engine

Responsável por:

- registrar tentativas
- rastrear decisões
- manter trilha de segurança
- suportar relatórios e exportação

## Fases de Evolução

### MVP

- monólito modular em FastAPI
- PostgreSQL para persistência principal
- Redis para cache, rate limit e sessões auxiliares
- WebSocket para progresso de verificação

### Fase Avançada

- workers assíncronos com Celery
- filas para processamento pesado
- embeddings com pgvector
- anti-spoofing mais robusto

### Fase Enterprise

- separação de serviços
- observabilidade completa
- tenancy mais forte
- Kubernetes e IaC

## Princípios de Dados

- armazenar embeddings em vez de mídia bruta sempre que possível
- versionar modelos biométricos
- separar dados de auditoria dos dados operacionais
- registrar consentimento, IP, dispositivo e timestamps

## Fronteiras Técnicas

BioGate AI deve operar com inteligência comportamental realista:

- padrões de acesso
- deriva de score
- variação de dispositivo
- risco contextual

Ele não deve alegar:

- leitura de ondas cerebrais por webcam
- diagnóstico emocional
- sincronização neural remota como funcionalidade de produto real
