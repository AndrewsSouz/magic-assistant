# Magic Assistant MVP

Backend Python para analisar decklists de Magic: The Gathering com dados da Scryfall.

## O que já faz
- recebe decklist em texto
- separa mainboard e sideboard
- busca as cartas na Scryfall
- retorna análise heurística inicial
- pronto para deploy no Railway via Docker

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger:
- `http://localhost:8000/docs`

Healthcheck:
- `http://localhost:8000/health`

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
