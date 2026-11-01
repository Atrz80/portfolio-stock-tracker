"""Compatibility entry point for ``uvicorn main:app``.

The implementation lives in the :mod:`app` package; this module preserves the
existing public startup command and Docker configuration.
"""

from app.main import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
