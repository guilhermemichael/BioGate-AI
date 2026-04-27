# BioGate AI API Draft

## Base Path

```txt
/api/v1
```

## Endpoints Prioritários do MVP

### `POST /auth/register`

Cria a conta inicial do usuário e registra o consentimento biométrico.

### `POST /auth/login`

Valida credenciais primárias e inicia o fluxo de desafio biométrico.

### `POST /biometric/enroll`

Recebe amostras faciais e vocais para criação do perfil biométrico.

### `POST /biometric/check-in`

Recebe a tentativa biométrica do login, calcula scores e retorna a decisão.

### `GET /dashboard/summary`

Retorna métricas agregadas para o painel principal.

### `GET /audit/logs`

Retorna o histórico paginado de tentativas e eventos de segurança.

### `WS /ws/check-in`

Canal de feedback em tempo real durante o processamento biométrico.

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

## Eventos de WebSocket Planejados

- `CAPTURE_STARTED`
- `FACE_DETECTED`
- `FACE_ANALYZING`
- `VOICE_RECORDING`
- `VOICE_ANALYZING`
- `PHRASE_TRANSCRIBED`
- `RISK_CALCULATED`
- `DECISION_READY`
