# ticker_agent.py
"""
Ticker resolution agent.

Takes a free-form user query that mentions a company name and resolves it to
the appropriate NSE / BSE ticker symbol using a local JSON mapping. Wrapped
as a single-tool LangChain agent so the upstream stock-analysis flow can call
it as part of a larger agentic pipeline.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict

from langchain.agents import Tool, initialize_agent

from ai_stock_agent import ask_stock_question
from llm_groq import llm


# Path to the BSE/NSE ticker mapping JSON.
# Override at runtime via the BSE_TICKER_PATH env var; defaults to a file
# alongside this module.
DEFAULT_TICKER_PATH = Path(__file__).parent / "bse_ticker_mapping.json"
TICKER_PATH = Path(os.environ.get("BSE_TICKER_PATH", DEFAULT_TICKER_PATH))


class TickerExtractionTool:
    """Resolves a company name in a query to a BSE/NSE ticker symbol."""

    _TICKER_PATTERN = re.compile(r"\b[A-Z]{2,5}\.(?:BO|NS)\b")

    def __init__(self, json_path: str | os.PathLike) -> None:
        self.json_path = Path(json_path)
        self.ticker_mapping: Dict[str, str] = self._load_ticker_mapping()

    def _load_ticker_mapping(self) -> Dict[str, str]:
        try:
            with self.json_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[ticker_agent] mapping file not found at {self.json_path}")
            return {}
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[ticker_agent] error loading ticker mapping: {exc}")
            return {}

    def extract_ticker(self, query: str) -> str:
        """Return a human-readable instruction string with the resolved ticker.

        Behavior:
        - If the query already contains an explicit ticker (e.g. ``RELIANCE.NS``),
          use it directly.
        - Otherwise scan the company-name -> ticker mapping for a match against
          significant words in the query (length > 2).
        """
        # 1) Already-formed ticker present in the query?
        match = self._TICKER_PATTERN.search(query)
        if match:
            ticker_symbol = match.group()
            for company_name, mapped in self.ticker_mapping.items():
                if mapped == ticker_symbol:
                    return (
                        f"Use ticker '{ticker_symbol}' for stock data and "
                        f"company name '{company_name}' for news search"
                    )
            return f"Use ticker '{ticker_symbol}' for all operations"

        # 2) Fuzzy match by company name words
        query_lower = query.lower()
        for company_name, ticker in self.ticker_mapping.items():
            words = [w for w in company_name.lower().split() if len(w) > 2]
            if any(word in query_lower for word in words):
                return (
                    f"Use ticker '{ticker}' for stock data and "
                    f"company name '{company_name}' for news search"
                )

        return "No ticker symbol found in the mapping for this query."


def create_ticker_agent(json_path: str | os.PathLike = TICKER_PATH):
    """Build a LangChain agent with a single ticker-extraction tool."""
    ticker_tool = TickerExtractionTool(json_path)

    tools = [
        Tool(
            name="ticker_extractor",
            description=(
                "Extract a stock ticker symbol from a company name using the "
                "BSE/NSE mapping. Returns the ticker plus the canonical company "
                "name that should be used for news search."
            ),
            func=ticker_tool.extract_ticker,
        )
    ]

    return initialize_agent(
        tools=tools,
        llm=llm,
        agent="zero-shot-react-description",
        verbose=True,
    )


def analyze_stock_with_ticker_agent(query: str):
    """End-to-end flow: resolve ticker, then run the stock analysis agent."""
    ticker_agent = create_ticker_agent()

    ticker_response = ticker_agent.invoke(
        {"input": f"Extract the stock ticker symbol from this query: {query}"}
    )
    raw = ticker_response.get("output", "")
    print("Ticker raw extraction response:", raw)

    # Trim a trailing exchange suffix (e.g. ``RELIANCE.NS`` -> ``RELIANCE``)
    # so downstream tools that don't expect the suffix still work.
    if "." in raw:
        raw = raw.split(".")[0]
    print("Ticker final extraction response:", raw)

    return ask_stock_question(query)


if __name__ == "__main__":
    demo_query = (
        "Give me detailed insights about vedanta stock including trend and metrics"
    )
    print(analyze_stock_with_ticker_agent(demo_query))
