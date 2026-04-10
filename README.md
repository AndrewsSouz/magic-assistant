# Magic Assistant MVP

Backend Python para analisar decklists de Magic: The Gathering com provedores de cartas e analise heuristica inicial, com enriquecimento opcional via LLM.

Versao atual:
- `v0.1.0`
- primeira versao funcional sem integracao com LLM

## O que já faz
- recebe decklist em texto
- separa mainboard e sideboard
- busca cartas via MTG API com fallback para Scryfall
- retorna análise heurística inicial
- usa OpenAI opcionalmente para refinar resumo, pontos fortes, pontos fracos e sugestões
- pronto para deploy no Railway via Docker

## Documentacao
- arquitetura: `docs/architecture.md`
- roadmap: `docs/roadmap.md`

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Swagger:
- `http://localhost:8000/docs`

Healthcheck:
- `http://localhost:8000/health`

Logs:
- por padrão vão para `logs/magic-assistant.log`
- para mudar o caminho, define `APP_LOG_FILE`

LLM opcional:
- define `OPENAI_API_KEY` para ativar a análise via OpenAI
- o modelo padrão é `gpt-5.4-mini`, configurável por `OPENAI_MODEL`
- sem chave, ou em caso de erro na chamada, a API continua respondendo com a heurística local

## Exemplo de request

```bash
curl -X POST http://localhost:8000/analyze-deck \
  -H "Content-Type: application/json" \
  -d '{
    "decklist": "4 Lightning Bolt\n4 Monastery Swiftspear\n4 Lava Spike\n20 Mountain\n\nSideboard\n2 Smash to Smithereens"
  }'
```

## Deploy no Railway
1. Cria um repositório no GitHub e sobe estes arquivos.
2. No Railway, cria um novo projeto a partir do repo.
3. O `railway.json` já está configurado para build por Dockerfile.
4. Define a variável `PORT` se quiser, embora o Railway já injete isso normalmente.
5. Publica.

## Próximos passos
- integrar LLM para análise semântica de deck
- cache de cartas
- persistir análises
- suportar sugestões de upgrade por budget/formato
- adicionar front-end web
