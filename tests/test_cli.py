from ragprep import HashingEmbedder, Index
from ragprep.cli import main

DOCS = {
    "refund.md": "Customers can request a full refund within thirty days of delivery if the item is unused.",
    "shipping.md": "Express shipping delivers the next business day when you order before two in the afternoon.",
}


def test_stats_reports_counts_and_coverage_per_model(tmp_path, capsys):
    db = tmp_path / "index.sqlite"
    Index(db).sync(DOCS)
    Index(db, embedder=HashingEmbedder(dim=128)).sync({"refund.md": DOCS["refund.md"]})

    assert main(["stats", "--db", str(db)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "documents=1 chunks=1 embeddings=2",
        "hashing-128: 1/1 chunks embedded",
        "hashing-256: 1/1 chunks embedded",
    ]


def test_stats_on_a_missing_index_fails_without_creating_it(tmp_path, capsys):
    db = tmp_path / "missing.sqlite"
    assert main(["stats", "--db", str(db)]) == 1
    assert "no index" in capsys.readouterr().err
    assert not db.exists()
