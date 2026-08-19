from app.flags.citation_laundering import check_citation_laundering


def test_citation_laundering_detected():
    chains = [
        ["paper_a", "root_1"],
        ["paper_b", "root_1"],
        ["paper_c", "root_1"],
    ]

    result = check_citation_laundering(chains)

    assert result is not None
    assert result["flag_type"] == "citation_laundering"
    assert result["severity"] == "medium"


def test_independent_sources_not_flagged():
    chains = [
        ["paper_a", "root_1"],
        ["paper_b", "root_2"],
        ["paper_c", "root_3"],
    ]

    result = check_citation_laundering(chains)

    assert result is None


def test_too_few_sources_not_flagged():
    chains = [
        ["paper_a", "root_1"],
        ["paper_b", "root_1"],
    ]

    result = check_citation_laundering(chains)

    assert result is None