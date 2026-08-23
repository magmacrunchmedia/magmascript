"""Tests for the Mac domain.

The parsers and registration are tested without a network. The live SSH path is
exercised by hand (see the mac domain wiki page); these cover the logic that can
regress silently.
"""

from __future__ import annotations

from magmascript.domains.mac.tools import (
    MacProcess,
    MacSystemInfo,
    _format_membytes,
    parse_processes,
    parse_system_info,
)


SAMPLE_INFO = """HOSTNAME:Jake's MacBook Pro
OS:macOS 26.5.2
UPTIME:17 days, 51 mins
CPU:Apple M5 Pro
CORES:15
MEMBYTES:25769803776
LOAD: 1.62 1.64 1.68"""


class TestParseSystemInfo:
    def test_maps_every_field(self):
        info = parse_system_info(SAMPLE_INFO)
        assert info == MacSystemInfo(
            hostname="Jake's MacBook Pro",
            os_version="macOS 26.5.2",
            uptime="17 days, 51 mins",
            cpu_name="Apple M5 Pro",
            cpu_cores="15",
            memory="24GB",
            load="1.62 1.64 1.68",
        )

    def test_membytes_becomes_gib(self):
        assert parse_system_info(SAMPLE_INFO).memory == "24GB"

    def test_hostname_with_colon_survives(self):
        # split(":", 1) keeps everything after the first colon.
        info = parse_system_info("HOSTNAME:name: with colon\nOS:macOS 26")
        assert info.hostname == "name: with colon"

    def test_unknown_lines_ignored(self):
        info = parse_system_info("HOSTNAME:mac\nGARBAGE\nNOISE:xyz\nOS:macOS 26")
        assert info.hostname == "mac"
        assert info.os_version == "macOS 26"

    def test_missing_fields_default_empty(self):
        info = parse_system_info("HOSTNAME:mac")
        assert info.hostname == "mac"
        assert info.cpu_name == ""
        assert info.memory == ""


class TestFormatMembytes:
    def test_whole_gib(self):
        assert _format_membytes(str(16 * 1024 ** 3)) == "16GB"

    def test_rounds_to_nearest(self):
        assert _format_membytes("25769803776") == "24GB"

    def test_non_numeric_passes_through(self):
        assert _format_membytes("N/A") == "N/A"


class TestParseProcesses:
    SAMPLE = """  PID %CPU %MEM COMM
88248 19.0  1.2 parsecd
  398 14.6  0.8 WindowServer
27809  9.5  0.3 sshd-session: jakemccoy [priv]"""

    def test_skips_header(self):
        procs = parse_processes(self.SAMPLE)
        assert len(procs) == 3
        assert all(isinstance(p, MacProcess) for p in procs)

    def test_first_row(self):
        first = parse_processes(self.SAMPLE)[0]
        assert first == MacProcess(pid="88248", cpu="19.0", mem="1.2", command="parsecd")

    def test_command_keeps_spaces(self):
        procs = parse_processes(self.SAMPLE)
        assert procs[2].command == "sshd-session: jakemccoy [priv]"

    def test_blank_lines_ignored(self):
        assert parse_processes("\n\n" + self.SAMPLE + "\n\n") == parse_processes(self.SAMPLE)

    def test_empty_input(self):
        assert parse_processes("") == []


class TestRegistration:
    def test_mac_domain_is_registered(self):
        import magmascript.domains  # noqa: F401 — triggers registration
        from magmascript.core.registry import list_domains

        assert "mac" in list_domains()

    def test_client_reads_mac_config(self):
        from magmascript.core.config import Config, MacConfig
        from magmascript.domains.mac import MacClient

        cfg = Config(mac=MacConfig(host="1.2.3.4", user="someone"))
        client = MacClient(cfg)
        assert client._host == "1.2.3.4"
        assert client._user == "someone"

    def test_env_var_overrides_host(self, monkeypatch):
        monkeypatch.setenv("MAGMA_MAC_HOST", "9.9.9.9")
        from magmascript.core.config import load_config

        assert load_config().mac.host == "9.9.9.9"
