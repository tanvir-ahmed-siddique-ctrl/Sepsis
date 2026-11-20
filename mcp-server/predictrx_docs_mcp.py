"""PredictRx docs MCP — versioned safety/model/onboarding markdown for AI assistants.

Split from the ops server so documentation agents can load cards without ops tools.
Run (stdio):  python mcp-server/predictrx_docs_mcp.py
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "model-card": ROOT / "docs" / "model-card.md",
    "safety-ethics": ROOT / "docs" / "safety-ethics.md",
    "hospital-onboarding": ROOT / "docs" / "hospital-onboarding.md",
}

server = MCPServer(
    name="predictrx-docs",
    title="PredictRx Sentinel (documentation)",
    instructions=(
        "Read-only PredictRx documentation resources. No patient data. "
        "Model card and safety text are research-prototype disclosures — not clinical approval."
    ),
    version="1.0.0",
)


def _doc(key: str) -> str:
    return DOCS[key].read_text(encoding="utf-8")


@server.resource("predictrx://docs/model-card", name="Model card", mime_type="text/markdown")
def model_card_doc() -> str:
    return _doc("model-card")


@server.resource("predictrx://docs/safety-ethics", name="Safety and ethics", mime_type="text/markdown")
def safety_doc() -> str:
    return _doc("safety-ethics")


@server.resource("predictrx://docs/hospital-onboarding", name="Hospital onboarding", mime_type="text/markdown")
def onboarding_doc() -> str:
    return _doc("hospital-onboarding")


if __name__ == "__main__":
    server.run("stdio")
