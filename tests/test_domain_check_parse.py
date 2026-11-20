"""Tests for the output parsers in scripts/domain_check.py.

Windows support lives or dies on these parsers: localised Windows
builds print Chinese labels ("DNS 服务器", "邮件交换器"), and a parser
that only understands the English wording silently finds no resolver
and no MX records.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

from domain_check import decode_output, parse_ipconfig, parse_nslookup_mx, parse_resolv_conf  # noqa: E402


NSLOOKUP_EN = """\
Server:  dns.google
Address:  8.8.8.8

Non-authoritative answer:
gmail.com	MX preference = 5, mail exchanger = gmail-smtp-in.l.google.com.
gmail.com	MX preference = 10, mail exchanger = alt1.gmail-smtp-in.l.google.com.
"""

NSLOOKUP_ZH = """\
服务器:  dns.google
Address:  8.8.8.8

非权威应答:
gmail.com	MX preference = 5, 邮件交换器 = gmail-smtp-in.l.google.com
gmail.com	MX preference = 10, 邮件交换器 = alt1.gmail-smtp-in.l.google.com
"""

IPCONFIG_EN = """\
Windows IP Configuration

Ethernet adapter Ethernet:

   Connection-specific DNS Suffix  . : lan
   IPv4 Address. . . . . . . . . . . : 192.168.1.50
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
   DNS Servers . . . . . . . . . . . : 192.168.1.1
                                       223.5.5.5
   NetBIOS over Tcpip. . . . . . . . : Enabled
"""

IPCONFIG_ZH = """\
Windows IP 配置

以太网适配器 以太网:

   连接特定的 DNS 后缀 . . . . . . . : lan
   IPv4 地址 . . . . . . . . . . . . : 192.168.1.50
   子网掩码  . . . . . . . . . . . . : 255.255.255.0
   默认网关. . . . . . . . . . . . . : 192.168.1.1
   DNS 服务器  . . . . . . . . . . . : 223.5.5.5
                                       192.168.1.1
   NetBIOS over Tcpip. . . . . . . . : 已启用
"""


class TestNslookupParse(unittest.TestCase):
    def test_english_mail_exchanger(self):
        self.assertEqual(
            parse_nslookup_mx(NSLOOKUP_EN),
            ["gmail-smtp-in.l.google.com",
             "alt1.gmail-smtp-in.l.google.com"])

    def test_chinese_mail_exchanger(self):
        self.assertEqual(
            parse_nslookup_mx(NSLOOKUP_ZH),
            ["gmail-smtp-in.l.google.com",
             "alt1.gmail-smtp-in.l.google.com"])

    def test_no_mx_lines(self):
        self.assertEqual(parse_nslookup_mx("Server: dns.google\n"), [])


class TestIpconfigParse(unittest.TestCase):
    def test_english_dns_servers_with_continuation(self):
        self.assertEqual(parse_ipconfig(IPCONFIG_EN),
                         ["192.168.1.1", "223.5.5.5"])

    def test_chinese_dns_servers_with_continuation(self):
        self.assertEqual(parse_ipconfig(IPCONFIG_ZH),
                         ["223.5.5.5", "192.168.1.1"])

    def test_no_dns_label(self):
        self.assertEqual(parse_ipconfig("Windows IP Configuration\n"), [])


class TestDecodeOutput(unittest.TestCase):
    def test_gbk_nslookup_output_decodes_and_parses(self):
        # A Chinese Windows console emits GBK bytes. Decoding them as
        # UTF-8 raised UnicodeDecodeError out of the subprocess helpers
        # (and a traceback in doctor); decode_output must recover the
        # text so the MX records survive.
        raw = NSLOOKUP_ZH.encode("gbk")
        self.assertEqual(
            parse_nslookup_mx(decode_output(raw)),
            ["gmail-smtp-in.l.google.com",
             "alt1.gmail-smtp-in.l.google.com"])

    def test_gbk_ipconfig_output_decodes_and_parses(self):
        raw = IPCONFIG_ZH.encode("gbk")
        self.assertEqual(parse_ipconfig(decode_output(raw)),
                         ["223.5.5.5", "192.168.1.1"])

    def test_invalid_bytes_never_raise(self):
        text = decode_output(b"\xff\xfe\x00\x80abc\x81\x82\xff")
        self.assertIsInstance(text, str)

    def test_none_and_str_passthrough(self):
        self.assertEqual(decode_output(None), "")
        self.assertEqual(decode_output("already text"), "already text")


class TestResolvConfParse(unittest.TestCase):
    def test_nameservers(self):
        text = "# comment\nnameserver 192.168.1.1\nsearch lan\nnameserver 8.8.8.8\n"
        self.assertEqual(parse_resolv_conf(text),
                         ["192.168.1.1", "8.8.8.8"])


if __name__ == "__main__":
    unittest.main()
