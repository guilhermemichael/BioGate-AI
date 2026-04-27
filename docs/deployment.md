# BioGate AI Deployment Notes

## MVP

Infraestrutura recomendada:

- backend FastAPI em container
- PostgreSQL gerenciado ou local via Docker
- Redis para cache e suporte a filas
- frontend Next.js
- object storage compatível com S3 quando necessário

## Compose Local

Serviços previstos:

- `backend`
- `postgres`
- `redis`

## Produção Inicial

- deploy simples em Railway, Render, Fly.io ou VPS
- CI/CD com GitHub Actions
- segredos por variáveis de ambiente
- logs centralizados

## Produção Avançada

- worker separado
- filas assíncronas
- observabilidade
- storage criptografado
- banco gerenciado
- reverse proxy
- WAF e rate limiting
