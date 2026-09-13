from pathlib import Path


class ObsidianKnowledgeStore:
    """Local knowledge store backed by an Obsidian Markdown vault."""

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path).expanduser().resolve()

    def list_notes(self) -> list[Path]:
        """Return all Markdown notes using paths relative to the vault."""
        if not self.vault_path.is_dir():
            raise FileNotFoundError(
                f"Obsidian vault does not exist: {self.vault_path}"
            )

        return sorted(
            path.relative_to(self.vault_path)
            for path in self.vault_path.rglob("*.md")
            if path.is_file()
        )

    def read_note(self, relative_path: str | Path) -> str:
        """Read a Markdown note inside the vault."""
        path = self._safe_path(relative_path)

        if not path.is_file():
            raise FileNotFoundError(f"Obsidian note does not exist: {relative_path}")

        return path.read_text(encoding="utf-8")

    def write_note(self, relative_path: str | Path, content: str) -> None:
        """Create or replace a Markdown note inside the vault."""
        path = self._safe_path(relative_path)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def search(self, query: str) -> list[Path]:
        """Return notes containing the query, using case-insensitive text search."""
        if not query.strip():
            raise ValueError("query must not be empty")

        query_lower = query.casefold()
        matches: list[Path] = []

        for relative_path in self.list_notes():
            content = self.read_note(relative_path)

            if query_lower in content.casefold():
                matches.append(relative_path)

        return matches

    def _safe_path(self, relative_path: str | Path) -> Path:
        """Resolve a vault-relative path without allowing vault escape."""
        candidate = (self.vault_path / Path(relative_path)).resolve()

        try:
            candidate.relative_to(self.vault_path)
        except ValueError as exc:
            raise ValueError(
                f"Path escapes the Obsidian vault: {relative_path}"
            ) from exc

        return candidate