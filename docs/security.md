# BioGate AI Security Baseline

## Objetivo

Definir a linha de base de segurança para o MVP e as fases seguintes do produto.

## Controles Obrigatórios

- Hash de senha com Argon2id
- JWT com expiração curta
- refresh token rotativo
- rate limit por IP e por usuário
- bloqueio temporário após falhas consecutivas
- criptografia de embeddings biométricos
- auditoria de eventos sensíveis
- TLS em trânsito
- segregação entre dados operacionais e de auditoria

## Proteção de Dados Biométricos

- Preferir embeddings em vez de imagem e áudio brutos
- Armazenar mídia bruta somente quando houver justificativa, consentimento e retenção definida
- Versionar o modelo usado para gerar embeddings
- Permitir revogação e exclusão dos dados biométricos

## Segurança de Aplicação

- Validação estrita com Pydantic
- Sanitização de inputs
- tratamento explícito de erros
- logging estruturado
- segredos fora do código-fonte

## Segurança Operacional

- PostgreSQL com credenciais fortes
- Redis sem exposição pública
- backups testados
- revisão de acessos administrativos
- observabilidade para tentativas suspeitas

## Regras de Produto

O projeto não deve:

- vender biometria como infalível
- tomar decisões irreversíveis com base em um único score
- esconder do usuário a finalidade do dado biométrico

O projeto deve:

- explicar a decisão
- registrar a decisão
- oferecer caminhos de recuperação de acesso
