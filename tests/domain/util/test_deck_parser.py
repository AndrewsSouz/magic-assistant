from app.domain.util.deck_parser import parse_decklist


def test_parse_simple_mainboard_lines() -> None:
    parsed = parse_decklist(
        """
        4 Lightning Bolt
        3x Monastery Swiftspear
        """
    )

    assert len(parsed.mainboard) == 2
    assert parsed.mainboard[0].quantity == 4
    assert parsed.mainboard[0].card_name == "Lightning Bolt"
    assert parsed.mainboard[0].set_code is None
    assert parsed.mainboard[0].collector_number is None
    assert parsed.mainboard[1].quantity == 3
    assert parsed.mainboard[1].card_name == "Monastery Swiftspear"


def test_parse_set_and_collector_number() -> None:
    parsed = parse_decklist(
        """
        4 Lightning Bolt (M11) 146
        2 Counterspell (DMR) 52
        """
    )

    assert parsed.mainboard[0].card_name == "Lightning Bolt"
    assert parsed.mainboard[0].set_code == "M11"
    assert parsed.mainboard[0].collector_number == "146"
    assert parsed.mainboard[1].set_code == "DMR"
    assert parsed.mainboard[1].collector_number == "52"


def test_parse_collector_number_without_set() -> None:
    parsed = parse_decklist(
        """
        4 Swamp (#238)
        2x Mountain (#239)
        """
    )

    assert parsed.mainboard[0].card_name == "Swamp"
    assert parsed.mainboard[0].collector_number == "238"
    assert parsed.mainboard[0].set_code is None
    assert parsed.mainboard[1].card_name == "Mountain"
    assert parsed.mainboard[1].collector_number == "239"


def test_parse_sideboard_and_detected_sections() -> None:
    parsed = parse_decklist(
        """
        Deck
        4 Lightning Bolt
        Sideboard
        2 Pyroblast
        """
    )

    assert parsed.detected_sections == ["Deck", "Sideboard"]
    assert len(parsed.mainboard) == 1
    assert len(parsed.sideboard) == 1
    assert parsed.mainboard[0].zone == "mainboard"
    assert parsed.sideboard[0].zone == "sideboard"
    assert parsed.sideboard[0].card_name == "Pyroblast"


def test_parse_implicit_sideboard_after_blank_line() -> None:
    parsed = parse_decklist(
        """
        4 Lightning Bolt
        2 Chain Lightning

        2 Pyroblast
        1 Red Elemental Blast
        """
    )

    assert len(parsed.mainboard) == 2
    assert len(parsed.sideboard) == 2
    assert parsed.mainboard[0].zone == "mainboard"
    assert parsed.sideboard[0].zone == "sideboard"
    assert parsed.sideboard[0].card_name == "Pyroblast"


def test_ignore_counted_section_headers() -> None:
    parsed = parse_decklist(
        """
        12 CREATURES
        4 Llanowar Elves
        8 INSTANTS and SORC.
        4 Lightning Bolt
        """
    )

    assert parsed.detected_sections == ["12 CREATURES", "8 INSTANTS and SORC."]
    assert len(parsed.mainboard) == 2
    assert parsed.mainboard[0].card_name == "Llanowar Elves"
    assert parsed.mainboard[1].card_name == "Lightning Bolt"
    assert parsed.unparsed_lines == []


def test_collect_unparsed_lines_and_warnings() -> None:
    parsed = parse_decklist(
        """
        4 Lightning Bolt
        not a valid line
        Sideboard
        ????
        """
    )

    assert parsed.unparsed_lines == ["not a valid line", "????"]
    assert parsed.warnings == ["2 line(s) could not be parsed."]
