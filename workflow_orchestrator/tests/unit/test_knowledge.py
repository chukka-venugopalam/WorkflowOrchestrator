"""Unit tests for Knowledge system."""

from __future__ import annotations

import tempfile
from pathlib import Path

from workflow_orchestrator.knowledge.knowledge_base import KnowledgeBase
from workflow_orchestrator.knowledge.knowledge_index import KnowledgeIndex
from workflow_orchestrator.knowledge.knowledge_loader import KnowledgeLoader
from workflow_orchestrator.knowledge.knowledge_models import KnowledgeCategory, KnowledgeEntry
from workflow_orchestrator.knowledge.knowledge_search import KnowledgeSearch
from workflow_orchestrator.knowledge.knowledge_store import KnowledgeStore


class TestKnowledgeStore:
    """Tests for KnowledgeStore."""

    def setup_method(self) -> None:
        self.store = KnowledgeStore()

    def test_create(self) -> None:
        entry = self.store.create("Test", "Content", KnowledgeCategory.GENERAL)
        assert entry.title == "Test"
        assert entry.content == "Content"

    def test_get(self) -> None:
        entry = self.store.create("Test", "Content")
        found = self.store.get(entry.entry_id)
        assert found is not None
        assert found.title == "Test"

    def test_get_not_found(self) -> None:
        assert self.store.get("nonexistent") is None

    def test_update(self) -> None:
        entry = self.store.create("Test", "Original")
        self.store.update(entry.entry_id, content="Updated")
        updated = self.store.get(entry.entry_id)
        assert updated is not None
        assert updated.content == "Updated"

    def test_remove(self) -> None:
        entry = self.store.create("Test", "Content")
        assert self.store.remove(entry.entry_id)
        assert self.store.get(entry.entry_id) is None

    def test_list_by_category(self) -> None:
        self.store.create("A", "Content", KnowledgeCategory.ARCHITECTURE_DECISION)
        self.store.create("B", "Content", KnowledgeCategory.ARCHITECTURE_DECISION)
        entries = self.store.list_by_category(KnowledgeCategory.ARCHITECTURE_DECISION)
        assert len(entries) == 2

    def test_count(self) -> None:
        assert self.store.count == 0
        self.store.create("Test", "Content")
        assert self.store.count == 1

    def test_file_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "knowledge.json"
            store = KnowledgeStore(file_path=file_path)
            store.create("Test", "Content")
            assert file_path.exists()


class TestKnowledgeIndex:
    """Tests for KnowledgeIndex."""

    def setup_method(self) -> None:
        self.index = KnowledgeIndex()

    def _make_entry(self, title: str, content: str, category=KnowledgeCategory.GENERAL, tags=None):
        return KnowledgeEntry(
            entry_id=title.lower().replace(" ", "_"),
            title=title,
            content=content,
            category=category,
            tags=tags or [],
        )

    def test_add_and_search(self) -> None:
        entry = self._make_entry("Python Best Practices", "Use type hints and docstrings")
        self.index.add_entry(entry)
        results = self.index.search("python type hints")
        assert len(results) > 0
        assert results[0].score > 0

    def test_search_empty(self) -> None:
        results = self.index.search("")
        assert results == []

    def test_search_by_tag(self) -> None:
        entry = self._make_entry("Test", "Content", tags=["python", "testing"])
        self.index.add_entry(entry)
        results = self.index.search_by_tag("python")
        assert len(results) > 0

    def test_search_by_category(self) -> None:
        entry = self._make_entry("ADR-1", "Decision", KnowledgeCategory.ARCHITECTURE_DECISION)
        self.index.add_entry(entry)
        results = self.index.search_by_category(KnowledgeCategory.ARCHITECTURE_DECISION)
        assert len(results) > 0

    def test_remove_entry(self) -> None:
        entry = self._make_entry("Test", "Content")
        self.index.add_entry(entry)
        assert self.index.remove_entry(entry.entry_id)
        assert self.index.count == 0


class TestKnowledgeSearch:
    """Tests for KnowledgeSearch."""

    def setup_method(self) -> None:
        self.index = KnowledgeIndex()
        self.search = KnowledgeSearch(self.index)
        self._populate()

    def _populate(self) -> None:
        entries = [
            KnowledgeEntry(entry_id="e1", title="Python Intro", content="Python is for programming", category=KnowledgeCategory.GENERAL, tags=["python"]),
            KnowledgeEntry(entry_id="e2", title="TypeScript Setup", content="TypeScript adds types", category=KnowledgeCategory.CODING_STANDARD, tags=["typescript"]),
            KnowledgeEntry(entry_id="e3", title="ADR-001", content="Use monorepo architecture", category=KnowledgeCategory.ARCHITECTURE_DECISION, tags=["architecture"]),
        ]
        for e in entries:
            self.index.add_entry(e)

    def test_search(self) -> None:
        results = self.search.search("python")
        assert len(results) >= 1

    def test_search_by_category(self) -> None:
        results = self.search.search_by_category(KnowledgeCategory.ARCHITECTURE_DECISION)
        assert len(results) >= 1

    def test_search_by_tags_any(self) -> None:
        results = self.search.search_by_tags(["python", "typescript"], require_all=False)
        assert len(results) >= 2

    def test_search_by_tags_all(self) -> None:
        results = self.search.search_by_tags(["python"], require_all=True)
        assert len(results) >= 1

    def test_search_with_min_score(self) -> None:
        results = self.search.search("python", min_score=0.01)
        assert len(results) >= 1

    def test_search_no_results(self) -> None:
        results = self.search.search("zzzznonexistent")
        assert len(results) == 0


class TestKnowledgeBase:
    """Tests for KnowledgeBase."""

    def setup_method(self) -> None:
        self.kb = KnowledgeBase()

    def test_add_and_get(self) -> None:
        entry = self.kb.add("Test Entry", "Content", KnowledgeCategory.GENERAL)
        found = self.kb.get(entry.entry_id)
        assert found is not None
        assert found.title == "Test Entry"

    def test_search(self) -> None:
        self.kb.add("Python Guide", "Python dependency injection guide", KnowledgeCategory.GENERAL)
        results = self.kb.search("python dependency")
        assert len(results) > 0

    def test_search_no_results(self) -> None:
        results = self.kb.search("nonexistent")
        assert len(results) == 0


class TestKnowledgeLoader:
    """Tests for KnowledgeLoader."""

    def setup_method(self) -> None:
        self.loader = KnowledgeLoader()

    def test_load_missing_file(self) -> None:
        entries = self.loader.load_file("/nonexistent/file.yaml")
        assert entries == []

    def test_load_missing_directory(self) -> None:
        entries = self.loader.load_directory("/nonexistent/dir")
        assert entries == []

    def test_load_json(self, tmp_path: Path) -> None:
        json_file = tmp_path / "test_knowledge.json"
        json_file.write_text('{"title": "Test", "content": "Test content", "category": "general"}')
        entries = self.loader.load_file(json_file)
        assert len(entries) == 1
        assert entries[0].title == "Test"

    def test_load_markdown(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test_knowledge.md"
        md_file.write_text("---\ntitle: My Knowledge\ncategory: coding_standard\ntags: [python]\n---\nContent here")
        entries = self.loader.load_file(md_file)
        assert len(entries) >= 1
