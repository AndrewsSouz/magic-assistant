from __future__ import annotations

from app.domain.models.card.card_data import CardData
from app.integration.llm_integration import LlmIntegration


class LlmAnalysisService:
    def __init__(self, llm_integration: LlmIntegration) -> None:
        self._llm_integration = llm_integration

    @property
    def enabled(self) -> bool:
        return self._llm_integration.enabled

    async def analyze(
        self,
        cards: list[CardData],
        format_guess: str,
        goal: str | None,
        heuristic_result: dict,
    ) -> dict | None:
        if not self.enabled:
            return None

        prompt = self._build_prompt(
            cards=cards,
            format_guess=format_guess,
            goal=goal,
            heuristic_result=heuristic_result,
        )
        result = await self._llm_integration.generate_deck_analysis(prompt)
        if not result:
            return None

        summary = str(result.get("summary") or "").strip()
        strengths = [str(item).strip() for item in result.get("strengths") or [] if str(item).strip()]
        weaknesses = [str(item).strip() for item in result.get("weaknesses") or [] if str(item).strip()]
        suggestions = [str(item).strip() for item in result.get("suggestions") or [] if str(item).strip()]

        if not summary:
            return None

        merged_result = dict(heuristic_result)
        merged_result.update(
            {
                "summary": summary,
                "strengths": strengths or heuristic_result["strengths"],
                "weaknesses": weaknesses or heuristic_result["weaknesses"],
                "suggestions": suggestions or heuristic_result["suggestions"],
            }
        )
        return merged_result

    def _build_prompt(
        self,
        cards: list[CardData],
        format_guess: str,
        goal: str | None,
        heuristic_result: dict,
    ) -> str:
        mainboard_cards = [card for card in cards if not card.sideboard]
        sideboard_cards = [card for card in cards if card.sideboard]
        mainboard_count = sum(card.quantity for card in mainboard_cards)
        sideboard_count = sum(card.quantity for card in sideboard_cards)
        mainboard_lines = [
            self._format_card_context(card)
            for card in mainboard_cards
        ]
        sideboard_lines = [
            self._format_card_context(card)
            for card in sideboard_cards
        ]

        return (
            "Analise este deck de Magic de forma objetiva e confiavel.\n"
            "Considere todas as cartas e todos os campos fornecidos no contexto.\n"
            "Use a heuristica do sistema apenas como apoio, nao como verdade absoluta.\n"
            "Se houver incerteza, seja conservador e explicito.\n\n"
            f"Objetivo do usuário: {goal or 'general improvement'}\n"
            f"Formato provável: {format_guess}\n"
            f"Contagem do mainboard: {mainboard_count}\n"
            f"Contagem do sideboard: {sideboard_count}\n"
            f"Contagem total: {mainboard_count + sideboard_count}\n\n"
            "Heurística atual do sistema:\n"
            f"- Resumo: {heuristic_result['summary']}\n"
            f"- Pontos fortes: {heuristic_result['strengths']}\n"
            f"- Pontos fracos: {heuristic_result['weaknesses']}\n"
            f"- Sugestões: {heuristic_result['suggestions']}\n\n"
            "Mainboard completo com dados enriquecidos:\n"
            f"{chr(10).join(mainboard_lines) if mainboard_lines else 'vazio'}\n\n"
            "Sideboard completo com dados enriquecidos:\n"
            f"{chr(10).join(sideboard_lines) if sideboard_lines else 'vazio'}\n\n"
            "Orcamento da resposta:\n"
            '- Retorne somente JSON valido com as chaves "summary", "strengths", "weaknesses" e "suggestions".\n'
            '- "summary": exatamente 2 ou 3 frases curtas.\n'
            '- "strengths": exatamente 3 itens, cada item com 1 frase curta.\n'
            '- "weaknesses": exatamente 3 itens, cada item com 1 frase curta.\n'
            '- "suggestions": exatamente 3 itens, cada item com 1 frase curta; cite nomes de cartas apenas quando o contexto sustentar isso.\n'
            "- Nao repita o mesmo ponto em campos diferentes.\n"
            "- Nao use markdown, comentarios, texto fora do JSON ou chaves extras.\n"
        )

    @staticmethod
    def _format_card_context(card: CardData) -> str:
        oracle_text = (card.oracle_text or "").replace("\n", " ").strip() or "desconhecido"
        colors = ", ".join(card.colors) if card.colors else "nenhuma"
        color_identity = ", ".join(card.color_identity) if card.color_identity else "nenhuma"
        legalities = ", ".join(
            f"{str(fmt)}={str(status)}"
            for fmt, status in sorted((card.legalities or {}).items(), key=lambda item: str(item[0]))
        ) or "desconhecido"

        return (
            f"- name={card.name}; "
            f"quantity={card.quantity}; "
            f"mana_cost={card.mana_cost or 'desconhecido'}; "
            f"cmc={card.cmc if card.cmc is not None else 'desconhecido'}; "
            f"type_line={card.type_line or 'desconhecido'}; "
            f"oracle_text={oracle_text}; "
            f"colors=[{colors}]; "
            f"color_identity=[{color_identity}]; "
            f"legalities=[{legalities}]"
        )
