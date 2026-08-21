import pytest

from app.sources.arxiv import parse_arxiv_atom, parse_arxiv_id

ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2310.12345v2</id>
    <updated>2023-10-20T17:59:59Z</updated>
    <published>2023-10-19T17:59:59Z</published>
    <title>Claim Verification with
      Retrieval-Augmented Transformers
    </title>
    <summary>Abstract text.</summary>
    <author>
      <name>Jane Doe</name>
    </author>
    <author>
      <name>John Smith</name>
    </author>
    <arxiv:journal_ref>Nature 2023</arxiv:journal_ref>
    <arxiv:doi>10.1000/example</arxiv:doi>
  </entry>
</feed>
"""


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("https://arxiv.org/abs/2310.12345", "2310.12345"),
        ("https://arxiv.org/pdf/2310.12345v2.pdf", "2310.12345v2"),
        ("http://export.arxiv.org/abs/cs/0212001", "cs/0212001"),
        ("2310.12345", "2310.12345"),
        ("see arxiv.org/abs/2401.00001v1 for details", "2401.00001v1"),
    ],
)
def test_parse_arxiv_id(source, expected):
    assert parse_arxiv_id(source) == expected


def test_parse_arxiv_id_rejects_garbage():
    with pytest.raises(ValueError):
        parse_arxiv_id("https://example.com/not-arxiv")


def test_parse_arxiv_atom_extracts_metadata():
    meta = parse_arxiv_atom(ATOM_XML)

    assert meta["title"] == (
        "Claim Verification with Retrieval-Augmented Transformers"
    )
    assert meta["authors"] == ["Jane Doe", "John Smith"]
    assert meta["year"] == 2023
    assert meta["doi"] == "10.1000/example"
    assert meta["journal"] == "Nature 2023"


def test_parse_arxiv_atom_without_entry():
    import pytest

    with pytest.raises(ValueError):
        parse_arxiv_atom(
            '<?xml version="1.0"?><feed '
            'xmlns="http://www.w3.org/2005/Atom"></feed>'
        )
