from ragprep import Index
from ragprep.cli import main

TEXT = {
    "faq.md": "Customers can request a full refund within thirty days of delivery if the item is unused.",
    "drafts/new-policy.md": "Draft: refunds might be extended to sixty days for loyalty members next year.",
    "notes.txt": "Express shipping delivers the next business day when you order before two in the afternoon.",
}


def write_docs(root):
    for rel, text in TEXT.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def indexed_docs(index):
    return sorted(row[0] for row in index.db.execute("SELECT doc_id FROM documents"))


def test_excluded_paths_are_not_indexed(tmp_path):
    docs = write_docs(tmp_path / "docs")
    index = Index()
    stats = index.sync_folder(docs, exclude=["drafts/*", "*.txt"])
    assert stats.added == 1
    assert indexed_docs(index) == ["faq.md"]


def test_excluding_an_indexed_file_removes_it(tmp_path):
    docs = write_docs(tmp_path / "docs")
    index = Index()
    index.sync_folder(docs)
    assert len(indexed_docs(index)) == 3
    stats = index.sync_folder(docs, exclude=["drafts/*"])
    assert stats.deleted == 1 and stats.unchanged == 2
    assert "drafts/new-policy.md" not in indexed_docs(index)


def test_cli_exclude_is_repeatable(tmp_path, capsys):
    docs = write_docs(tmp_path / "docs")
    db = tmp_path / "index.sqlite"
    args = ["ingest", str(docs), "--db", str(db), "--exclude", "drafts/*", "--exclude", "notes.txt"]
    assert main(args) == 0
    assert capsys.readouterr().out.startswith("added=1 ")
    assert indexed_docs(Index(db)) == ["faq.md"]
