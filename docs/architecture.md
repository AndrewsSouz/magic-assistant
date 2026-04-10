# Architecture

## Current Version

Nome sugerido desta etapa:
- `Magic Assistant MVP v0.1`
- subtitulo opcional: `Deck Analysis Core`

Esta versao representa a primeira entrega funcional sem integracao com LLM. O sistema ja consegue:
- receber decklists em texto
- fazer parsing de mainboard e sideboard
- enriquecer cartas via provedores externos
- gerar analise heuristica inicial
- expor tudo via API HTTP

## Current Structure

Arquivos e responsabilidades atuais:
- `main.py`: entrypoint ASGI
- `app/api`: criacao da aplicacao FastAPI, middlewares e dependency wiring
- `app/contract`: rotas HTTP e modelos de request/response
- `app/domain/models`: modelos centrais de deck e carta
- `app/domain/service`: servicos de orquestracao e heuristicas de analise
- `app/domain/util`: parsing e normalizacao da decklist
- `app/integration`: integracao com provedores externos de cartas
- `app/config/logging_config.py`: configuracao de logs

## Recommended Modularization

Antes de extrair microservicos, o melhor caminho e evoluir para um monolito modular. A proposta e separar o sistema por responsabilidade de negocio:

### `app/api`
- rotas FastAPI
- serializacao HTTP
- tratamento de erros HTTP

### `app/domain`
- entidades centrais como deck, carta analisada e resultado de analise
- regras de negocio que nao dependem de provider externo

### `app/domain/service`
- orquestracao de casos de uso
- exemplo: `analyze_deck_service`, `card_lookup_service`

### `app/integration`
- clientes externos
- exemplo: `mtg_api_client`, `scryfall_client`, futuro `llm_client`

### `app/config`
- configuracoes de ambiente
- politicas de timeout, rate limit e logging

## Near-Term Target

Objetivo da proxima iteracao:
- manter uma API unica
- modularizar o codigo para isolar integracoes externas
- preparar uma porta clara para integrar o servico de LLM

Uma boa fronteira para a LLM e:
- entrada: deck parseado + cartas enriquecidas + metadados opcionais
- saida: resumo, pontos fortes, pontos fracos, sugestoes e cortes/adicoes

## Future Service Boundaries

Se o sistema crescer, estas sao fronteiras naturais para futura extracao:
- `card-catalog-service`: responsavel por resolver e normalizar dados de carta
- `deck-analysis-service`: responsavel por heuristica e enriquecimento do deck
- `llm-orchestration-service`: responsavel por prompts, contexto, budget de tokens e respostas do modelo

Essas fronteiras so valem a pena quando houver ao menos um destes sinais:
- necessidade de escalar partes diferentes de forma independente
- ownership por times diferentes
- filas/processamento assincrono mais forte
- latencia ou custo exigindo isolamento operacional

## Guiding Principle

Por enquanto:
- modularizar primeiro
- extrair depois

Isso reduz complexidade cedo demais e deixa a evolucao para microservicos muito mais segura.
