from typing import Optional

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from mcp.server.fastmcp import FastMCP
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

mcp = FastMCP("Web Search")


@mcp.tool()
def web_search(
    query: str,
    max_results: int = 5,
    region: str = "us-en",
    safesearch: str = "moderate",
) -> str:
    """
    Search the web and return a list of matching results.

    Use this whenever the user asks about something that requires current
    or external information you would not already know — recent events,
    facts, people, products, documentation, etc.

    Args:
        query: The search query (e.g. "latest Python 3.13 release notes")
        max_results: How many results to return (default 5, max recommended 10)
        region: Search region/locale, e.g. "us-en", "uk-en", "in-en" (default "us-en")
        safesearch: One of "on", "moderate", "off" (default "moderate")

    Returns:
        A formatted string with each result's title, URL, and snippet, or an
        error / "no results" message.

    Example calls:
    - "What's the latest news on the James Webb telescope?"
    - "Search for how to configure nginx reverse proxy"
    - "Find documentation for the Python requests library"
    """
    try:
        max_results = max(1, min(int(max_results), 20))

        results = DDGS().text(
            query,
            region=region,
            safesearch=safesearch,
            max_results=max_results,
        )

        if not results:
            return f"No results found for: {query}"

        formatted = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "Untitled")
            href = r.get("href", "")
            body = r.get("body", "").strip()
            formatted.append(f"{i}. {title}\n   URL: {href}\n   {body}")

        return "\n\n".join(formatted)

    except DDGSException as e:
        return f"❌ Search error: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected error while searching: {str(e)}"


@mcp.tool()
def fetch_page_text(url: str, max_chars: int = 4000) -> str:
    """
    Fetch a URL and extract its readable text content (no summarization).

    Use this after web_search, when the user wants more detail from a
    specific result than the search snippet provides.

    Args:
        url: The full URL to fetch (must start with http:// or https://)
        max_chars: Maximum number of characters of extracted text to return
                   (default 4000, to keep responses manageable)

    Returns:
        The extracted page text (markdown-ish plain text), truncated to
        max_chars, or an error message.

    Example calls:
    - "Get more detail from that first result"
    - "Fetch https://example.com/article and summarize it"
    """
    try:
        if not (url.startswith("http://") or url.startswith("https://")):
            return "❌ Error: url must start with http:// or https://"

        result = DDGS().extract(url, fmt="text_markdown")
        content = result.get("content", "")

        if not content:
            return f"No extractable text content found at {url}"

        content = content.strip()
        if len(content) > max_chars:
            content = content[:max_chars].rstrip() + "\n...[truncated]"

        return content

    except DDGSException as e:
        return f"❌ Fetch error: {str(e)}"
    except Exception as e:
        return f"❌ Unexpected error while fetching page: {str(e)}"


if __name__ == "__main__":
    print("🔎 Web Search Service Starting...", file=sys.stderr)
    mcp.run()