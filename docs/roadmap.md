# Roadmap

## Versioning

Versao atual sugerida:
- `v0.1.0`
- nome: `Magic Assistant MVP`
- marco: `primeira versao funcional sem LLM`

## Delivered In v0.1

- endpoint de analise de deck funcionando
- parsing de decklist com suporte a separacao de sideboard
- normalizacao de nomes vindos de formatos como ManaBox
- integracao com provedores de cartas
- fallback entre provedores
- logging em arquivo e console
- analise heuristica inicial sem modelo de linguagem

## Next Step: v0.2

Foco:
- modularizar o backend para preparar a integracao com LLM

Entregas sugeridas:
- reorganizar pacotes em `api`, `services`, `integrations`, `domain` e `config`
- criar um servico de lookup de cartas desacoplado do endpoint
- criar um servico de analise desacoplado da camada HTTP
- documentar contratos internos principais

## Next Step After That: v0.3

Foco:
- primeira integracao com LLM

Entregas sugeridas:
- criar interface para provider de LLM
- montar contexto da lista a partir do deck parseado e cartas enriquecidas
- gerar analise textual mais rica
- manter heuristica local como fallback

## Technical Priorities

- adicionar cache simples de cartas com TTL e limite de tamanho
- deduplicar consultas por carta dentro da mesma request
- melhorar testes automatizados
- centralizar configuracoes via ambiente
- revisar timeouts e politicas de fallback

## Product Priorities

- analise por formato
- sugestoes de upgrade
- plano de sideboard
- historico de analises
- interface web
