#!/usr/bin/env python3
"""Unified web search + fetch adapter for the B2B outreach system.

Purpose: discovery (finding companies, decision-makers) and verification
(exact-match search for candidate emails) must NOT depend on whichever
built-in search the host agent happens to have. Any agent that can run
Python can call this script and get identical search behaviour.

Providers (first configured key wins, in this order):
  1. Serper  (Google index)  env SERPER_API_KEY   https://serper.dev
  2. Tavily                  env TAVILY_API_KEY   https://tavily.com
  3. Brave Search            env BRAVE_API_KEY    https://brave.com/search/api

If no key is configured the script exits with code 3 and prints a
FALLBACK notice: the executing agent should use its own built-in web
search instead and treat result coverage as degraded.

Usage:
  python3 web_search.py search "botanical garden gift shop buyer" [--num 10] [--country de] [--lang de]
  python3 web_search.py exact "jane.doe@example-company.com"
  python3 web_search.py fetch "https://example.com/impressum"

Output: JSON on stdout. `search`/`exact` return
  {"provider": ..., "query": ..., "results": [{"title","url","snippet"}]}
`fetch` returns {"url": ..., "text": ...} (plain text, truncated).
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def _post(url, payload, headers, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _get(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def search_serper(q, num, country, lang, key):
    payload = {"q": q, "num": num}
    if country:
        payload["gl"] = country
    if lang:
        payload["hl"] = lang
    d = _post("https://google.serper.dev/search", payload, {"X-API-KEY": key})
    return [{"title": x.get("title", ""), "url": x.get("link", ""), "snippet": x.get("snippet", "")}
            for x in d.get("organic", [])]


def search_tavily(q, num, country, lang, key):
    payload = {"query": q, "max_results": num, "search_depth": "basic"}
    d = _post("https://api.tavily.com/search", payload, {"Authorization": f"Bearer {key}"})
    return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", "")[:400]}
            for x in d.get("results", [])]


def search_brave(q, num, country, lang, key):
    from urllib.parse import urlencode
    qs = urlencode({"q": q, "count": num, **({"country": country} if country else {})})
    d = _get(f"https://api.search.brave.com/res/v1/web/search?{qs}",
             {"X-Subscription-Token": key, "Accept": "application/json"})
    return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("description", "")}
            for x in d.get("web", {}).get("results", [])]


PROVIDERS = [
    ("SERPER_API_KEY", "serper", search_serper),
    ("TAVILY_API_KEY", "tavily", search_tavily),
    ("BRAVE_API_KEY", "brave", search_brave),
]


def do_search(query, num, country, lang):
    for env, name, fn in PROVIDERS:
        key = os.environ.get(env)
        if key:
            try:
                results = fn(query, num, country, lang, key)
                return {"provider": name, "query": query, "results": results}
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
                print(json.dumps({"provider": name, "error": str(e)}), file=sys.stderr)
                continue
    print("FALLBACK: no search API key configured (SERPER_API_KEY / TAVILY_API_KEY / "
          "BRAVE_API_KEY). Use the executing agent's built-in web search instead; "
          "treat coverage as degraded and say so in the run log.", file=sys.stderr)
    sys.exit(3)


def do_fetch(url, max_chars=20000):
    import re
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "replace")
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {"url": url, "text": text[:max_chars]}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("search", "exact"):
        p = sub.add_parser(name)
        p.add_argument("query")
        p.add_argument("--num", type=int, default=10)
        p.add_argument("--country", default="")
        p.add_argument("--lang", default="")
    pf = sub.add_parser("fetch")
    pf.add_argument("url")
    args = ap.parse_args()
    if args.cmd == "fetch":
        print(json.dumps(do_fetch(args.url), ensure_ascii=False))
    else:
        q = f'"{args.query}"' if args.cmd == "exact" else args.query
        print(json.dumps(do_search(q, args.num, args.country, args.lang), ensure_ascii=False))


if __name__ == "__main__":
    main()
