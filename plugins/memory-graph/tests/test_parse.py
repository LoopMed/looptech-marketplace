from pathlib import Path

from memory_graph.parse import extract_links, parse_file, scan_dir

FRONTMATTER_DOC = """---
name: my-test-memory
description: A memory used for testing.
metadata:
  type: project
---

# Title

See also [[other-memory]] and [[other-memory]] again (duplicate),
plus [[third-memory|alias]] and [[fourth-memory#section]].
"""

NO_FRONTMATTER_DOC = """# Just an index

- [some link](other.md)
"""


def test_extract_links_dedupes_and_strips_alias_and_section():
    links = extract_links(
        "[[a]] [[b|Alias]] [[c#Section]] [[a]] [[  d  ]]"
    )
    assert links == ["a", "b", "c", "d"]


def test_parse_file_reads_frontmatter_and_links(tmp_path: Path):
    md = tmp_path / "my_test_memory.md"
    md.write_text(FRONTMATTER_DOC, encoding="utf-8")

    doc = parse_file(md)

    assert doc is not None
    assert doc.name == "my-test-memory"
    assert doc.description == "A memory used for testing."
    assert doc.type == "project"
    assert doc.links == ["other-memory", "third-memory", "fourth-memory"]
    assert "Title" in doc.body
    assert doc.path == str(md)
    assert doc.hash


def test_parse_file_returns_none_without_frontmatter(tmp_path: Path):
    md = tmp_path / "MEMORY.md"
    md.write_text(NO_FRONTMATTER_DOC, encoding="utf-8")

    assert parse_file(md) is None


def test_parse_file_falls_back_to_filename_stem_when_name_missing(tmp_path: Path):
    md = tmp_path / "unnamed.md"
    md.write_text(
        "---\ndescription: no name field\nmetadata:\n  type: reference\n---\nBody\n",
        encoding="utf-8",
    )

    doc = parse_file(md)
    assert doc is not None
    assert doc.name == "unnamed"


def test_scan_dir_skips_index_and_parses_memories(tmp_path: Path):
    (tmp_path / "MEMORY.md").write_text(NO_FRONTMATTER_DOC, encoding="utf-8")
    (tmp_path / "a.md").write_text(
        "---\nname: a\ndescription: A\nmetadata:\n  type: project\n---\nbody a\n",
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text(
        "---\nname: b\ndescription: B\nmetadata:\n  type: reference\n---\nbody b [[a]]\n",
        encoding="utf-8",
    )

    docs = scan_dir(str(tmp_path))
    names = sorted(d.name for d in docs)
    assert names == ["a", "b"]
