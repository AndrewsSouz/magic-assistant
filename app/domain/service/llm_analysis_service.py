from __future__ import annotations

from app.domain.models.card.card_data import CardData
from app.domain.models.deck.parsed_deck import ParsedDeck
from app.integration.llm_integration import LlmIntegration


class LlmAnalysisService:
    def __init__(self, llm_integration: LlmIntegration) -> None:
        self._llm_integration = llm_integration

    @property
    def enabled(self) -> bool:
        return self._llm_integration.enabled

    async def analyze(
        self,
        parsed_deck: ParsedDeck,
        cards: list[CardData],
        format_guess: str,
        goal: str | None,
        heuristic_result: dict,
    ) -> dict | None:
        if not self.enabled:
            return None

        prompt = self._build_prompt(
            parsed_deck=parsed_deck,
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
        parsed_deck: ParsedDeck,
        cards: list[CardData],
        format_guess: str,
        goal: str | None,
        heuristic_result: dict,
    ) -> str:
        mainboard_lines = [
            f"{entry.quantity}x {entry.card_name}"
            for entry in parsed_deck.mainboard
        ]
        sideboard_lines = [
            f"{entry.quantity}x {entry.card_name}"
            for entry in parsed_deck.sideboard
        ]
        card_notes = []
        for entry, card in zip(parsed_deck.mainboard, cards):
            details = []
            if card.type_line:
                details.append(card.type_line)
            if card.mana_cost:
                details.append(f"mana {card.mana_cost}")
            if card.oracle_text:
                oracle_excerpt = card.oracle_text.replace("\n", " ").strip()
                details.append(f"texto {oracle_excerpt[:220]}")
            card_notes.append(
                f"- {entry.card_name}: {' | '.join(details) if details else 'sem dados enriquecidos'}"
            )

        return (
            "Analise este deck de Magic de forma simples e prática.\n\n"
            f"Objetivo do usuário: {goal or 'general improvement'}\n"
            f"Formato provável: {format_guess}\n"
            f"Contagem do mainboard: {heuristic_result['card_count']}\n"
            f"Contagem do sideboard: {heuristic_result['sideboard_count']}\n\n"
            "Heurística atual do sistema:\n"
            f"- Resumo: {heuristic_result['summary']}\n"
            f"- Pontos fortes: {heuristic_result['strengths']}\n"
            f"- Pontos fracos: {heuristic_result['weaknesses']}\n"
            f"- Sugestões: {heuristic_result['suggestions']}\n\n"
            "Mainboard:\n"
            f"{chr(10).join(mainboard_lines) if mainboard_lines else 'vazio'}\n\n"
            "Sideboard:\n"
            f"{chr(10).join(sideboard_lines) if sideboard_lines else 'vazio'}\n\n"
            "Cartas enriquecidas:\n"
            f"{chr(10).join(card_notes) if card_notes else 'sem dados de cartas'}\n\n"
            "Retorne um JSON com:\n"
            '- "summary": um parágrafo curto\n'
            '- "strengths": lista com 2 a 4 itens\n'
            '- "weaknesses": lista com 2 a 4 itens\n'
            '- "suggestions": lista com 2 a 4 itens\n'
            "Evite repetir exatamente a heurística se puder refiná-la com o contexto disponível."
        )
