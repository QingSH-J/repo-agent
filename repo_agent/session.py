from pathlib import Path
class RepoSession:
    def __init__(self):
        self.repo_path : Path | None = None
        self.message : list[dict[str, str]] = []
        self.repo_files: list[str] = []
        self.repo_branch : str | None = None

    @property
    def is_repo_loaded(self) -> bool:
        return self.repo_path is not None