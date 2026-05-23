"""FastAPI 应用入口。"""

from __future__ import annotations

import uvicorn

from src.ai.api.app import app


def main() -> None:
    uvicorn.run("src.ai.api.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
