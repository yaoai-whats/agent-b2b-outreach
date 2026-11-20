#!/usr/bin/env python3
"""Domain checks: MX lookup and accept-all probe (docs/03, two steps).

Both checks are independent and both run before any candidate work on a
domain:

(a) MX lookup. A minimal DNS query for MX records, hand-built over UDP
    using only the standard library. If the UDP query fails (no resolver
    reachable, truncated answer, parse error), the system `nslookup`
    subprocess is tried as a fallback.
(b) Accept-all probe. Opens an SMTP conversation with the first MX host
    on port 25 (EHLO, MAIL FROM, RCPT TO a random non-existent local
    part). Reply 250 means the domain accepts any address
    (accept_all = true); 550/551/553 means it does not (false); any
    network failure, timeout, or ambiguous reply means "unknown".
    Port 25 is blocked by many networks and hosts, so "unknown" is a
    common and honest result: it is recorded, never guessed.

CLI:
    python3 domain_check.py example.com
        -> {"domain": ..., "domain_mx": ["mx1...", ...],
            "domain_accept_all": true | false | "unknown"}

    python3 domain_check.py --leads data/leads.jsonl
        Prints a JSON report for every row missing domain_mx or
        domain_accept_all. Add --write to store the results back on the
        rows (domain_mx as a boolean, domain_accept_all as true, false,
        or null when the probe was "unknown").
"""
import argparse
import json
import random
import socket
import struct
import subprocess
import sys

DNS_PORT = 53
SMTP_PORT = 25
TIMEOUT = 8


# ---------------------------------------------------------------- MX lookup

def _dns_servers():
    servers = []
    try:
        with open("/etc/resolv.conf", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) == 2 and parts[0] == "nameserver":
                    servers.append(parts[1])
    except OSError:
        pass
    for fallback in ("8.8.8.8", "1.1.1.1"):
        if fallback not in servers:
            servers.append(fallback)
    return servers


def _build_query(domain, qtype=15):
    tid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    qname = b"".join(bytes([len(part)]) + part.encode()
                     for part in domain.rstrip(".").split(".")) + b"\x00"
    return tid, header + qname + struct.pack(">HH", qtype, 1)


def _read_name(data, offset):
    """Read a possibly compressed DNS name; return (name, next_offset)."""
    labels = []
    jumped = False
    next_offset = offset
    seen = 0
    while offset < len(data):
        length = data[offset]
        if length == 0:
            if not jumped:
                next_offset = offset + 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                break
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                next_offset = offset + 2
            offset = pointer
            jumped = True
            seen += 1
            if seen > 20:  # compression loop guard
                break
            continue
        offset += 1
        labels.append(data[offset:offset + length].decode("utf-8", "replace"))
        offset += length
    return ".".join(labels), next_offset


def _parse_mx(data, tid):
    if len(data) < 12:
        return []
    r_tid, _flags, qd, an, _ns, _ar = struct.unpack(">HHHHHH", data[:12])
    if r_tid != tid:
        return []
    offset = 12
    for _ in range(qd):
        _name, offset = _read_name(data, offset)
        offset += 4
    records = []
    for _ in range(an):
        _name, offset = _read_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, _rclass, _ttl, rdlen = struct.unpack(">HHIH", data[offset:offset + 10])
        offset += 10
        rdata_start = offset
        if rtype == 15 and rdlen >= 3:
            exchange, _ = _read_name(data, rdata_start + 2)
            records.append(exchange.rstrip("."))
        offset = rdata_start + rdlen
    return records


def mx_via_udp(domain):
    tid, packet = _build_query(domain)
    for server in _dns_servers():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(TIMEOUT)
            sock.sendto(packet, (server, DNS_PORT))
            data, _ = sock.recvfrom(4096)
            sock.close()
            records = _parse_mx(data, tid)
            if records:
                return records
        except OSError:
            continue
    return []


def mx_via_nslookup(domain):
    try:
        out = subprocess.run(["nslookup", "-type=mx", domain],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return []
    records = []
    for line in out.stdout.splitlines():
        if "mail exchanger" in line and "=" in line:
            host = line.rsplit("=", 1)[1].strip().rstrip(".")
            if host:
                records.append(host)
    return records


def mx_via_dig(domain):
    try:
        out = subprocess.run(["dig", "+short", "MX", domain],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return []
    records = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            host = parts[-1].strip().rstrip(".")
            if host:
                records.append(host)
    return records


def lookup_mx(domain):
    """MX hostnames for a domain; empty list when none are found."""
    records = mx_via_udp(domain)
    if not records:
        records = mx_via_nslookup(domain)
    if not records:
        records = mx_via_dig(domain)
    return records


# ---------------------------------------------------------- accept-all probe

def _smtp_reply(sock_file):
    line = sock_file.readline().decode("utf-8", "replace")
    code = line[:3]
    # Multi-line replies: keep reading until "250 " (space, not dash).
    while len(line) >= 4 and line[3] == "-":
        line = sock_file.readline().decode("utf-8", "replace")
    return code


def probe_accept_all(domain, mx_hosts):
    """true / false / "unknown" for the domain's accept-all behaviour."""
    if not mx_hosts:
        return "unknown"
    host = mx_hosts[0]
    try:
        sock = socket.create_connection((host, SMTP_PORT), timeout=TIMEOUT)
    except OSError:
        return "unknown"
    try:
        sock.settimeout(TIMEOUT)
        fh = sock.makefile("rb")
        if _smtp_reply(fh) != "220":
            return "unknown"
        sock.sendall(b"EHLO probe.local\r\n")
        if _smtp_reply(fh) not in ("250", "502", "504"):
            return "unknown"
        sock.sendall(b"MAIL FROM:<>\r\n")
        if _smtp_reply(fh) != "250":
            return "unknown"
        probe_local = "nonexistent-" + "".join(
            random.choice("0123456789abcdef") for _ in range(12))
        sock.sendall(f"RCPT TO:<{probe_local}@{domain}>\r\n".encode())
        code = _smtp_reply(fh)
        try:
            sock.sendall(b"QUIT\r\n")
        except OSError:
            pass
        if code == "250":
            return True
        if code in ("550", "551", "553"):
            return False
        return "unknown"
    except OSError:
        return "unknown"
    finally:
        try:
            sock.close()
        except OSError:
            pass


def check_domain(domain):
    mx = lookup_mx(domain)
    accept_all = probe_accept_all(domain, mx) if mx else "unknown"
    return {"domain": domain, "domain_mx": mx, "domain_accept_all": accept_all}


# ---------------------------------------------------------------------- CLI

def _needs_check(row):
    return row.get("domain_mx") is None or row.get("domain_accept_all") is None


def main():
    parser = argparse.ArgumentParser(
        description="MX lookup and accept-all probe for one domain or a leads file.")
    parser.add_argument("domain", nargs="?", help="Single domain to check.")
    parser.add_argument("--leads", default=None,
                        help="Path to a leads .jsonl file to check in bulk.")
    parser.add_argument("--write", action="store_true",
                        help="With --leads: write results back onto the rows.")
    args = parser.parse_args()

    if args.domain:
        print(json.dumps(check_domain(args.domain), ensure_ascii=False))
        return

    if not args.leads:
        parser.error("give a domain or --leads <file>")

    with open(args.leads, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    report = []
    changed = False
    for row in rows:
        domain = (row.get("domain") or "").strip()
        if not domain or not _needs_check(row):
            continue
        result = check_domain(domain)
        report.append(result)
        if args.write:
            row["domain_mx"] = bool(result["domain_mx"])
            row["domain_accept_all"] = (
                None if result["domain_accept_all"] == "unknown"
                else result["domain_accept_all"])
            changed = True
    print(json.dumps({"checked": len(report), "results": report},
                     ensure_ascii=False))
    if args.write and changed:
        with open(args.leads, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"wrote results back to {args.leads}", file=sys.stderr)


if __name__ == "__main__":
    main()
