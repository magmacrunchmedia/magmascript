"""Tests for the MC1 (Windows PC) domain.

Parsers and registration, without a network. Mirrors test_mac.py. These would
have caught the cpu_load / disk_free key-mapping bug fixed alongside them.
"""

from __future__ import annotations

from magmascript.domains.mc1.tools import (
    MC1PowerSettings,
    MC1ServiceStatus,
    MC1SystemInfo,
    _format_uptime,
    parse_power_settings,
    parse_service_list,
    parse_system_info,
)


SAMPLE_INFO = """HOSTNAME:MC1
UPTIME:07:33:06.0140847
MEMORY:31.7GB/7.6GB
CPU:4%
DISK:93.2% free
DISK_FREE_GB:776.9GB
CPU_NAME:AMD Ryzen 7 8700F 8-Core Processor
CPU_CORES:8
OS_VERSION:Microsoft Windows 11 Home"""


class TestParseServiceList:
    def test_running_service(self):
        svcs = parse_service_list("AmdPpkgSvc: Running")
        assert svcs == [MC1ServiceStatus(name="AmdPpkgSvc", status="Running", ok=True)]

    def test_ok_flag_reflects_running(self):
        svcs = parse_service_list("A: Running\nB: Stopped")
        assert [s.ok for s in svcs] == [True, False]

    def test_ok_is_case_insensitive(self):
        assert parse_service_list("X: running")[0].ok is True

    def test_blank_and_malformed_lines_ignored(self):
        svcs = parse_service_list("\nAmdPpkgSvc: Running\nno-colon-here\n")
        assert len(svcs) == 1

    def test_empty(self):
        assert parse_service_list("") == []


class TestParseSystemInfo:
    def test_all_fields_map(self):
        info = parse_system_info(SAMPLE_INFO)
        assert info.hostname == "MC1"
        assert info.memory == "31.7GB/7.6GB"
        assert info.disk_free_gb == "776.9GB"
        assert info.cpu_name == "AMD Ryzen 7 8700F 8-Core Processor"
        assert info.cpu_cores == "8"
        assert info.os_version == "Microsoft Windows 11 Home"

    def test_cpu_emitted_key_maps_to_cpu_load(self):
        # PowerShell emits CPU:, the field is cpu_load. Regression guard for the
        # key-mapping bug where cpu_load came back blank on every call.
        assert parse_system_info(SAMPLE_INFO).cpu_load == "4%"

    def test_disk_emitted_key_maps_to_disk_free(self):
        assert parse_system_info(SAMPLE_INFO).disk_free == "93.2% free"

    def test_uptime_is_humanized(self):
        # 07:33:06 has no day component.
        assert parse_system_info(SAMPLE_INFO).uptime == "7 hours, 33 mins, 6s"

    def test_os_version_with_colons_survives(self):
        info = parse_system_info("OS_VERSION:Windows 11: Pro")
        assert info.os_version == "Windows 11: Pro"

    def test_missing_fields_default_blank(self):
        info = parse_system_info("HOSTNAME:MC1")
        assert info.hostname == "MC1"
        assert info.cpu_load == ""


class TestFormatUptime:
    def test_no_day_component(self):
        assert _format_uptime("07:33:06.0140847") == "7 hours, 33 mins, 6s"

    def test_with_day_component(self):
        assert _format_uptime("1.03:05:36.7441121") == "1 day, 3 hours, 5 mins, 36s"

    def test_plural_days(self):
        assert _format_uptime("3.00:00:00") == "3 days"

    def test_zero_uptime(self):
        assert _format_uptime("00:00:00") == "0s"

    def test_non_numeric_time_component_returns_raw(self):
        # A non-numeric hours field makes int() raise, so the raw string is
        # returned unchanged rather than a wrong value.
        assert _format_uptime("1.aa:bb:cc") == "1.aa:bb:cc"

    def test_wordless_garbage_degrades_to_zero(self):
        # No colon and no digits parses cleanly to nothing → "0s". Documents the
        # actual (lenient) behavior rather than asserting it is ideal.
        assert _format_uptime("garbage") == "0s"


class TestParsePowerSettings:
    SAMPLE = """SLEEP_AC:30
SLEEP_DC:15
HIBERNATE_AC:0
HIBERNATE_DC:0
POWER_MODE:sleep
HIBERNATE_ENABLED:True"""

    def test_all_fields(self):
        ps = parse_power_settings(self.SAMPLE)
        assert ps == MC1PowerSettings(
            sleep_timeout_ac=30,
            sleep_timeout_dc=15,
            hibernate_timeout_ac=0,
            hibernate_timeout_dc=0,
            power_mode="sleep",
            hibernate_enabled=True,
        )

    def test_always_on_mode(self):
        ps = parse_power_settings("POWER_MODE:always-on\nHIBERNATE_ENABLED:False")
        assert ps.power_mode == "always-on"
        assert ps.hibernate_enabled is False

    def test_unknown_power_mode_falls_back_to_sleep(self):
        assert parse_power_settings("POWER_MODE:banana").power_mode == "sleep"

    def test_non_numeric_timeout_becomes_zero(self):
        assert parse_power_settings("SLEEP_AC:never").sleep_timeout_ac == 0


class TestRegistration:
    def test_mc1_domain_is_registered(self):
        import magmascript.domains  # noqa: F401 — triggers registration
        from magmascript.core.registry import list_domains

        assert "mc1" in list_domains()

    def test_client_reads_mc1_config(self):
        from magmascript.core.config import Config, MC1Config
        from magmascript.domains.mc1 import MC1Client

        cfg = Config(mc1=MC1Config(host="1.2.3.4", user="someone"))
        client = MC1Client(cfg)
        assert client._host == "1.2.3.4"
        assert client._user == "someone"

    def test_env_var_overrides_host(self, monkeypatch):
        monkeypatch.setenv("MAGMA_MC1_HOST", "9.9.9.9")
        from magmascript.core.config import load_config

        assert load_config().mc1.host == "9.9.9.9"
