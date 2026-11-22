#!/usr/bin/env python3
"""Unified web search + fetch adapter for the B2B outreach system.

Purpose: discovery (finding companies, decision-makers) and verification
(exact-match search for candidate emails) must NOT depend on whichever
built-in search the host agent happens to have. Any agent that can run
Python can call this script and get identical search behaviour.

Providers (first configured key wins, in this order):
  1. Serper  (Google index)  env SERPER_API_KEY     https://serper.dev
  2. Keenable                env KEENABLE_API_KEY   https://keenable.ai
  3. Tavily                  env TAVILY_API_KEY     https://tavily.com
  4. Exa                     env EXA_API_KEY        https://exa.ai
  5. Linkup                  env LINKUP_API_KEY     https://www.linkup.so
  6. Brave Search            env BRAVE_API_KEY      https://brave.com/search/api

All six have free tiers (registration only, no card): Serper grants a
one-off credit pack, Keenable a large monthly free allowance, Tavily a
monthly credit allowance, Exa a starting credit balance, Linkup a
monthly credit top-up, Brave a monthly free quota. Quotas change;
check each provider's site for the current numbers.

If no key is configured at all, the script tries Keenable's keyless
public endpoint (shared per-IP pool, 1,000 requests/hour) and marks
the output with a "note" saying so. Only if that also fails does the
script exit with code 3 and print a FALLBACK notice: the executing
agent should use its own built-in web search instead and treat result
coverage as degraded.

Usage:
  python3 web_search.py search "buyer category keyword" [--num 10] [--country de] [--lang de]
  python3 web_search.py exact "jane.doe@example-company.com"
  python3 web_search.py fetch "https://example.com/impressum"
  python3 web_search.py maps "buyer category in City" [--num 10] [--country de] [--lang de]
  python3 web_search.py trade "company name or product keyword" [--num 10]

Output: JSON on stdout. `search`/`exact`/`maps`/`trade` return
  {"provider": ..., "query": ..., "results": [{"title","url","snippet"}]}
`fetch` returns {"url": ..., "text": ...} (plain text, truncated).

Notes on the two specialised subcommands:
- `maps` uses Serper's /maps endpoint when a Serper key is configured
  (real place listings: name, address, website). With any other provider
  it falls back to a plain web search and says so in the output
  ("note": "maps endpoint unavailable ..."), so coverage is degraded,
  never silently different.
- `trade` searches the public pages of a trade-data site
  (site:importyeti.com). Be honest about what this is: trade-data sites
  have no public API, so this can only surface pages a search engine can
  see. Treat hits as a lead to open and verify with `fetch`, never as
  verified trade records.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

try:
    import _config  # noqa: F401  (side effect: loads repo-root .env)
except ImportError:
    pass

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


def _keenable_results(d):
    return [{"title": x.get("title", ""), "url": x.get("url", ""),
             "snippet": (x.get("snippet") or x.get("description") or "")[:400]}
            for x in d.get("results", [])]


def search_keenable(q, num, country, lang, key):
    payload = {"query": q, "max_results": num}
    d = _post("https://api.keenable.ai/v1/search", payload, {"X-API-Key": key})
    return _keenable_results(d)


def search_keenable_keyless(q, num):
    # Keenable's public twin endpoint: no key, rate-limited per egress IP
    # (1,000 requests/hour, shared with everyone on the same address).
    payload = {"query": q, "max_results": num}
    d = _post("https://api.keenable.ai/v1/search/public", payload,
              {"X-Keenable-Title": "agent-b2b-outreach"})
    return _keenable_results(d)


def search_exa(q, num, country, lang, key):
    payload = {"query": q, "type": "auto", "numResults": num,
               "contents": {"highlights": True}}
    d = _post("https://api.exa.ai/search", payload, {"x-api-key": key})
    out = []
    for x in d.get("results", []):
        snippet = " ".join(x.get("highlights") or []) or (x.get("text") or "")
        out.append({"title": x.get("title", ""), "url": x.get("url", ""),
                    "snippet": snippet[:400]})
    return out


def search_linkup(q, num, country, lang, key):
    payload = {"q": q, "depth": "standard", "outputType": "searchResults",
               "maxResults": num}
    d = _post("https://api.linkup.so/v1/search", payload,
              {"Authorization": f"Bearer {key}"})
    return [{"title": x.get("name", ""), "url": x.get("url", ""),
             "snippet": (x.get("content") or "")[:400]}
            for x in d.get("results", []) if x.get("type", "text") == "text"]


PROVIDERS = [
    ("SERPER_API_KEY", "serper", search_serper),
    ("KEENABLE_API_KEY", "keenable", search_keenable),
    ("TAVILY_API_KEY", "tavily", search_tavily),
    ("EXA_API_KEY", "exa", search_exa),
    ("LINKUP_API_KEY", "linkup", search_linkup),
    ("BRAVE_API_KEY", "brave", search_brave),
]

SEARCH_KEY_ENVS = " / ".join(env for env, _name, _fn in PROVIDERS)


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
    try:
        results = search_keenable_keyless(query, num)
        return {"provider": "keenable-keyless", "query": query, "results": results,
                "note": ("no search API key configured; served by Keenable's "
                         "keyless public endpoint (shared per-IP pool, 1,000 "
                         "requests/hour, queries logged by the provider). "
                         "Register a free key (KEENABLE_API_KEY) for reliable "
                         "volume, and treat exact-match hits from this tier as "
                         "unconfirmed until the page itself is opened.")}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
        print(json.dumps({"provider": "keenable-keyless", "error": str(e)}), file=sys.stderr)
    print(f"FALLBACK: no search API key configured ({SEARCH_KEY_ENVS}) and the "
          "keyless endpoint failed. Use the executing agent's built-in web "
          "search instead; treat coverage as degraded and say so in the run "
          "log.", file=sys.stderr)
    sys.exit(3)


def maps_serper(q, num, country, lang, key):
    payload = {"q": q}
    if country:
        payload["gl"] = country
    if lang:
        payload["hl"] = lang
    d = _post("https://google.serper.dev/maps", payload, {"X-API-KEY": key})
    results = []
    for x in d.get("places", [])[:num]:
        snippet_parts = [x.get("address", ""), x.get("type", "")]
        snippet = " · ".join(p for p in snippet_parts if p)
        results.append({"title": x.get("title", ""),
                        "url": x.get("website", ""),
                        "snippet": snippet})
    return results


def do_maps(query, num, country, lang):
    key = os.environ.get("SERPER_API_KEY")
    if key:
        try:
            return {"provider": "serper-maps", "query": query,
                    "results": maps_serper(query, num, country, lang, key)}
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ValueError) as e:
            print(json.dumps({"provider": "serper-maps", "error": str(e)}),
                  file=sys.stderr)
    out = do_search(query, num, country, lang)
    out["note"] = ("maps endpoint unavailable for the configured provider; "
                   "plain web search results instead, coverage degraded")
    return out


def do_trade(query, num):
    q = query if "importyeti.com" in query else f"site:importyeti.com {query}"
    out = do_search(q, num, "", "")
    out["note"] = ("trade-data sites have no public API; these are only "
                   "publicly searchable pages. Open and verify before "
                   "recording any trade signal.")
    return out


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
    for name in ("search", "exact", "maps"):
        p = sub.add_parser(name)
        p.add_argument("query")
        p.add_argument("--num", type=int, default=10)
        p.add_argument("--country", default="")
        p.add_argument("--lang", default="")
    pt = sub.add_parser("trade")
    pt.add_argument("query")
    pt.add_argument("--num", type=int, default=10)
    pf = sub.add_parser("fetch")
    pf.add_argument("url")
    args = ap.parse_args()
    if args.cmd == "fetch":
        print(json.dumps(do_fetch(args.url), ensure_ascii=False))
    elif args.cmd == "maps":
        print(json.dumps(do_maps(args.query, args.num, args.country,
                                 args.lang), ensure_ascii=False))
    elif args.cmd == "trade":
        print(json.dumps(do_trade(args.query, args.num), ensure_ascii=False))
    else:
        q = f'"{args.query}"' if args.cmd == "exact" else args.query
        print(json.dumps(do_search(q, args.num, args.country, args.lang), ensure_ascii=False))


if __name__ == "__main__":
    main()
