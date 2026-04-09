import re
from app.models import DeckEntry, ParsedDeck

LINE_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$", re.IGNORECASE)
MANABOX_SUFFIX_RE = re.compile(r"^(.*?)(?:\s+\(([A-Z0-9]+)\)\s+(\d+[A-Z]?))$", re.IGNORECASE)
SIDEBOARD_MARKERS = {"sideboard", "sideboard:", "side"}
MAINBOARD_MARKERS = {"mainboard", "mainboard:", "deck", "deck:"}


def normalize_card_name(name: str) -> str:
    normalized = re.sub(r"\s+", " ", name).strip()
    manabox_match = MANABOX_SUFFIX_RE.match(normalized)
    if manabox_match:
        return manabox_match.group(1).strip()
    return normalized


def parse_decklist(decklist: str) -> ParsedDeck:
    mainboard = []
    sideboard = []
    current_section = "mainboard"
    seen_mainboard_entries = False

    for raw_line in decklist.splitlines():
        line = raw_line.strip()
        if not line:
            if current_section == "mainboard" and seen_mainboard_entries:
                current_section = "sideboard"
            continue

        lower = line.lower()
        if lower in SIDEBOARD_MARKERS:
            current_section = "sideboard"
            continue
        if lower in MAINBOARD_MARKERS:
            current_section = "mainboard"
            continue

        match = LINE_RE.match(line)
        if not match:
            continue

        qty = int(match.group(1))
        card_name = normalize_card_name(match.group(2))
        entry = DeckEntry(quantity=qty, card_name=card_name)

        if current_section == "mainboard":
            mainboard.append(entry)
            seen_mainboard_entries = True
        else:
            sideboard.append(entry)

    return ParsedDeck(mainboard=mainboard, sideboard=sideboard)
