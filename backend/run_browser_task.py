import sys
import urllib.parse
from playwright.sync_api import sync_playwright

def print_search_results(page, max_results: int = 5):
    # Adjust the selector based on the actual page structure
    results = page.query_selector_all("div.news-card")
    if not results:
        print("No results found.")
        return
    count = 0
    for res in results:
        if count >= max_results:
            break
        title_elem = res.query_selector("h2")
        snippet_elem = res.query_selector("p")
        title_text = title_elem.inner_text().strip() if title_elem else "No title"
        link_href = title_elem.query_selector("a").get_attribute("href") if title_elem and title_elem.query_selector("a") else "No link"
        snippet_text = snippet_elem.inner_text().strip() if snippet_elem else ""
        output_line = f"{count+1}. {title_text}"
        if snippet_text:
            output_line += f" - {snippet_text}"
        if link_href:
            output_line += f" ({link_href})"
        print(output_line)
        count += 1


def print_page_text(page, max_chars: int = 5000):
    body = page.query_selector("body")
    text = body.inner_text() if body else ""
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "... (truncated)"
    print(text)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Error: Insufficient arguments. Usage: python run_browser_task.py [search|open] <query_or_url>", file=sys.stderr)
        sys.exit(1)
    mode = sys.argv[1].lower()
    query_or_url = " ".join(sys.argv[2:])
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            if mode == "search":
                query = urllib.parse.quote_plus(query_or_url)
                page.goto(f"https://www.bing.com/search?q={query}", wait_until="domcontentloaded", timeout=10000)
                print_search_results(page)
            elif mode == "open":
                url = query_or_url if query_or_url.startswith(("http://", "https://")) else "http://" + query_or_url
                page.goto(url, wait_until="networkidle", timeout=15000)
                print_page_text(page)
            else:
                print(f"Error: Unknown mode '{mode}'.", file=sys.stderr)
                browser.close()
                sys.exit(1)
            browser.close()
    except Exception as e:
        print(f"Exception in browser task: {e}", file=sys.stderr)
        sys.exit(1)
