import re

from app.domain.models.deck.deck_entry import DeckEntry
from app.domain.models.deck.parsed_deck import ParsedDeck

SIDEBOARD_MARKERS = {"sideboard", "sideboard:", "side", "side board", "side deck", "sb"}
MAINBOARD_MARKERS = {
    "mainboard",
    "mainboard:",
    "deck",
    "deck:",
    "main",
    "main board",
    "maindeck",
    "creatures",
    "lands",
    "spells",
    "instants",
    "sorceries",
    "instants and sorceries",
    "artifacts",
    "enchantments",
    "planeswalkers",
    "battles",
    "other spells",
    "commander",
    "companion",
}


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _normalize_section_name(line: str) -> str:
    normalized = line.strip().lower().rstrip(":")
    return re.sub(r"\s+", " ", normalized)


def _classify_section(line: str) -> str | None:
    normalized = _normalize_section_name(line)
    if normalized in SIDEBOARD_MARKERS:
        return "sideboard"
    if normalized in MAINBOARD_MARKERS:
        return "mainboard"
    return None


def _parse_card_line(line: str) -> DeckEntry | None:
    normalized_line = _normalize_line(line)

    match = re.match(
        r"^(?P<qty>\d+)\s*x?\s+(?P<name>.+?)\s+\((?P<set>[A-Za-z0-9]+)\)\s+(?P<number>[A-Za-z0-9]+)\s*$",
        normalized_line,
        re.IGNORECASE,
    )
    if match:
        card_name = match.group("name").strip()
        if _classify_section(card_name) is not None:
            return None
        return DeckEntry(
            quantity=int(match.group("qty")),
            card_name=card_name,
            raw_line=normalized_line,
            set_code=match.group("set").upper(),
            collector_number=match.group("number"),
        )

    match = re.match(
        r"^(?P<qty>\d+)\s*x?\s+(?P<name>.+?)\s+\(#(?P<number>[A-Za-z0-9]+)\)\s*$",
        normalized_line,
        re.IGNORECASE,
    )
    if match:
        card_name = match.group("name").strip()
        if _classify_section(card_name) is not None:
            return None
        return DeckEntry(
            quantity=int(match.group("qty")),
            card_name=card_name,
            raw_line=normalized_line,
            collector_number=match.group("number"),
        )

    match = re.match(
        r"^(?P<qty>\d+)\s*x?\s+(?P<name>.+?)\s*$",
        normalized_line,
        re.IGNORECASE,
    )
    if match:
        card_name = match.group("name").strip()
        if _classify_section(card_name) is not None:
            return None
        return DeckEntry(
            quantity=int(match.group("qty")),
            card_name=card_name,
            raw_line=normalized_line,
        )

    return None


def parse_decklist(decklist: str) -> ParsedDeck:
    mainboard = []
    sideboard = []
    unparsed_lines = []
    warnings = []
    detected_sections = []
    current_section = "mainboard"
    seen_mainboard_entries = False

    for raw_line in decklist.splitlines():
        line = _normalize_line(raw_line)
        if not line:
            if current_section == "mainboard" and seen_mainboard_entries:
                current_section = "sideboard"
            continue

        section_type = _classify_section(line)
        if section_type is not None:
            detected_sections.append(line)
            current_section = section_type
            continue

        entry = _parse_card_line(line)
        if entry is None:
            unparsed_lines.append(line)
            continue

        entry.zone = current_section
        if current_section == "sideboard":
            sideboard.append(entry)
        else:
            mainboard.append(entry)
            seen_mainboard_entries = True

    if unparsed_lines:
        warnings.append(f"{len(unparsed_lines)} line(s) could not be parsed.")

    return ParsedDeck(
        mainboard=mainboard,
        sideboard=sideboard,
        unparsed_lines=unparsed_lines,
        warnings=warnings,
        detected_sections=detected_sections,
    )
