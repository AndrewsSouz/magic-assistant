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
            f"{card.quantity}x {card.name}"
            for card in mainboard_cards
        ]
        sideboard_lines = [
            f"{card.quantity}x {card.name}"
            for card in sideboard_cards
        ]
        mainboard_notes = []
        for card in mainboard_cards:
            details = []
            if card.type_line:
                details.append(card.type_line)
            if card.mana_cost:
                details.append(f"mana {card.mana_cost}")
            if card.oracle_text:
                oracle_excerpt = card.oracle_text.replace("\n", " ").strip()
                details.append(f"texto {oracle_excerpt[:220]}")
            mainboard_notes.append(
                f"- {card.quantity}x {card.name}: {' | '.join(details) if details else 'sem dados enriquecidos'}"
            )

        sideboard_notes = []
        for card in sideboard_cards:
            details = []
            if card.type_line:
                details.append(card.type_line)
            if card.mana_cost:
                details.append(f"mana {card.mana_cost}")
            if card.oracle_text:
                oracle_excerpt = card.oracle_text.replace("\n", " ").strip()
                details.append(f"texto {oracle_excerpt[:220]}")
            sideboard_notes.append(
                f"- {card.quantity}x {card.name}: {' | '.join(details) if details else 'sem dados enriquecidos'}"
            )

        return (
            "Analise este deck de Magic de forma simples e prática.\n\n"
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
            "Mainboard (cartas principais):\n"
            f"{chr(10).join(mainboard_lines) if mainboard_lines else 'vazio'}\n\n"
            "Sideboard (cartas de reserva):\n"
            f"{chr(10).join(sideboard_lines) if sideboard_lines else 'vazio'}\n\n"
            "Cartas enriquecidas do mainboard:\n"
            f"{chr(10).join(mainboard_notes) if mainboard_notes else 'sem dados de cartas do mainboard'}\n\n"
            "Cartas enriquecidas do sideboard:\n"
            f"{chr(10).join(sideboard_notes) if sideboard_notes else 'sem dados de cartas do sideboard'}\n\n"
            "Retorne um JSON como passado no json schema:\n"
            '- "summary": um parágrafo explicando o deck\n'
            '- "strengths": lista com 2 a 4 itens\n'
            '- "weaknesses": lista com 2 a 4 itens\n'
            '- "suggestions": lista com 2 a 4 itens, citar nomes de cartas que encaixam na estratégia\n'
        )
