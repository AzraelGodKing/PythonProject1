from __future__ import annotations

import contextlib

import pytest

from arcade.core import paths


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Every test gets its own empty data directory."""
    root = tmp_path / "data"
    monkeypatch.setenv(paths.ENV_VAR, str(root))
    return root


@pytest.fixture
def tk_root(monkeypatch):
    """A hidden Tk root. Skips the test when no display is available."""
    tk = pytest.importorskip("tkinter")
    from tkinter import messagebox, simpledialog

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"no display: {exc}")
    root.withdraw()
    # Never block on a modal dialog during tests.
    for name in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, name, lambda *a, **k: "ok")
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(simpledialog, "askstring", lambda *a, **k: "Tester")
    yield root
    with contextlib.suppress(tk.TclError):
        root.destroy()
