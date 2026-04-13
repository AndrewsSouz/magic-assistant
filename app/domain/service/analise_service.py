from __future__ import annotations

from collections import Counter

from app.domain.models.card.card_data import CardData
from app.domain.models.deck.parsed_deck import ParsedDeck


def guess_format(parsed_deck: ParsedDeck) -> str:
    main_count = sum(item.quantity for item in parsed_deck.mainboard)
    side_count = sum(item.quantity for item in parsed_deck.sideboard)

    if main_count == 100:
        return "Commander provável"
    if main_count == 40:
        return "Limited provável"
    if side_count > 0:
        return "Constructed 60 cartas provável (BO3)"
    return "Constructed 60 cartas provável (BO1)"


def classify_game_plan(avg_cmc: float, creature_count: int, spell_count: int) -> str:
    if avg_cmc <= 2.3 and creature_count >= spell_count:
        return "aggro"
    if avg_cmc >= 3.5 and spell_count >= creature_count:
        return "control"
    if creature_count >= 10 and spell_count >= 10:
        return "midrange / tempo"
    return "plano híbrido"


def build_basic_analysis(parsed_deck: ParsedDeck, cards: list[CardData]) -> dict:
    color_counter = Counter()
    cmcs = []
    land_count = 0
    creature_count = 0
    noncreature_spell_count = 0

    for entry, card in zip(parsed_deck.mainboard, cards):
        for color in card.colors:
            color_counter[color] += entry.quantity

        type_line = (card.type_line or "").lower()
        if "land" in type_line:
            land_count += entry.quantity
        elif "creature" in type_line:
            creature_count += entry.quantity
        else:
            noncreature_spell_count += entry.quantity

        if card.cmc is not None and "land" not in type_line:
            cmcs.extend([card.cmc] * entry.quantity)

    main_count = sum(item.quantity for item in parsed_deck.mainboard)
    side_count = sum(item.quantity for item in parsed_deck.sideboard)
    avg_cmc = round(sum(cmcs) / len(cmcs), 2) if cmcs else 0.0
    game_plan = classify_game_plan(avg_cmc, creature_count, noncreature_spell_count)

    summary = (
        f"Deck com {main_count} cartas no mainboard e {side_count} no sideboard. "
        f"CMC médio dos spells: {avg_cmc}. "
        f"Plano provável: {game_plan}. "
        f"Cores predominantes: {dict(color_counter) if color_counter else 'incolor / artefatos / terrenos'}.")

    strengths = []
    weaknesses = []
    suggestions = []

    if avg_cmc and avg_cmc <= 2.3:
        strengths.append("Curva baixa; tende a pressionar cedo e aproveitar melhor o early game.")
    elif avg_cmc >= 3.8:
        strengths.append("Cartas mais pesadas sugerem potencial de impacto alto no mid/late game.")

    if land_count < 20 and main_count >= 60:
        weaknesses.append("Quantidade de terrenos possivelmente baixa para uma lista de 60 cartas.")
        suggestions.append("Revisar mana base; testar entre 22 e 25 terrenos conforme curva e formato.")
    elif land_count > 28 and main_count == 60:
        weaknesses.append("Quantidade de terrenos possivelmente alta para a média da curva.")
        suggestions.append("Avaliar cortar 1-2 terrenos para aumentar densidade de spells.")

    if len(color_counter) >= 3:
        weaknesses.append("Base de mana multicolor pode gerar inconsistência sem duals/fixes suficientes.")
        suggestions.append("Checar se as fontes de cor acompanham os custos mais exigentes da lista.")

    if creature_count < 8 and noncreature_spell_count > 20:
        strengths.append("Lista inclinada para spells, o que pode favorecer controle, combo ou tempo.")

    if not strengths:
        strengths.append("A lista já apresenta identidade inicial suficiente para testes e iteração.")

    if not weaknesses:
        weaknesses.append("Sem gargalo gritante detectado pela heurística básica; precisa de análise com contexto de formato.")

    suggestions.append("Adicionar camada de LLM para identificar cortes, adds e plano de sideboard por matchup.")

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "card_count": main_count,
        "sideboard_count": side_count,
    }
