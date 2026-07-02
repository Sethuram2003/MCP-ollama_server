# Web Search MCP Server

An MCP server that gives an LLM the ability to search the web and pull
readable text from a page, using DuckDuckGo (via the `ddgs` package) —
no API key required.

## Tools

### `web_search(query, max_results=5, region="us-en", safesearch="moderate")`
Searches the web and returns a formatted list of results (title, URL,
snippet).

### `fetch_page_text(url, max_chars=4000)`
Fetches a URL and extracts its readable text content, truncated to
`max_chars`. Useful after `web_search` when the user wants more detail
than the snippet gives.

## Setup

```bash
cd web_search
uv sync        # or: pip install -e .
```

## Run standalone

```bash
python web_search.py
```

## Use with the MCP client in this repo

```bash
cd client_mcp
python client.py ../web_search/web_search.py
```

## Notes

- No API key or account needed — `ddgs` scrapes public search engine
  results directly.
- Because it isn't a paid API, DuckDuckGo may occasionally rate-limit or
  block requests (you'll see this surfaced as a `❌ Search error:` message).
  If that happens repeatedly, wait a bit or reduce request frequency.
- `region` controls result locale (e.g. `"us-en"`, `"uk-en"`, `"in-en"`).
- `safesearch` accepts `"on"`, `"moderate"`, or `"off"`.