"""Unit tests for extract.py — pure logic with no Qt or network dependencies."""

import pytest
from extract import (
    is_blocked,
    needs_confirmation,
    nl_to_powershell,
    diagnose_error,
    format_snapshot,
    generate_health_alerts,
)


# ── is_blocked ──────────────────────────────────────────────────────────────

class TestIsBlocked:
    """Tests for the is_blocked command safety validator."""

    @pytest.mark.parametrize("command", [
        "format E: /fs:NTFS",
        "rm -rf /",
        "del /f /q C:\\Windows\\system32\\config",
        "reg delete HKLM\\System /va",
        "diskpart",
        "bcdedit /set {default} recoveryenabled No",
        "cipher /w:C",
        "net user administrator /delete",
        "shutdown /r /o",
        "takeown /f C:\\Windows",
        "icacls C:\\ /grant Everyone:F",
        "sc delete BITS",
        "netsh interface set interface Ethernet admin=disable",
        "powercfg -devicequery wake_armed",
        "fsutil behavior set disablelastaccess 1",
        "wevtutil cl System",
    ])
    def test_blocked_patterns(self, command: str) -> None:
        """All blocked patterns should be detected as unsafe."""
        assert is_blocked(command), f"Command should be blocked: {command}"

    @pytest.mark.parametrize("command", [
        "Get-Process",
        "notepad.exe",
        "echo hello world",
        "show RAM usage",
        "whoami",
        "ipconfig /all",
        "dir C:\\Users",
        "python --version",
        "calc.exe",
        "start chrome",
    ])
    def test_safe_commands(self, command: str) -> None:
        """Normal commands should NOT be blocked."""
        assert not is_blocked(command), f"Command should not be blocked: {command}"

    def test_empty_string(self) -> None:
        """Empty string should not be blocked."""
        assert not is_blocked("")

    def test_case_insensitivity(self) -> None:
        """Blocked pattern matching should be case-insensitive."""
        assert is_blocked("FORMAT D: /FS:NTFS")
        assert is_blocked("DiskPart")
        assert is_blocked("BCDEDIT /enum")


# ── needs_confirmation ─────────────────────────────────────────────────────

class TestNeedsConfirmation:
    """Tests for the needs_confirmation safety guard."""

    @pytest.mark.parametrize("command", [
        "del C:\\temp\\file.txt",
        "rmdir C:\\temp",
        "taskkill /f /im explorer.exe",
        "shutdown /s /t 0",
        "restart-computer",
        "format E:",
        "netsh reset",
        "Stop-Process -Name explorer",
        "Remove-Item C:\\test",
        "Clear-EventLog System",
        "Disable-NetAdapter Ethernet",
        "Set-Service wuauserv -StartupType Disabled",
        "sc config wuauserv start= disabled",
        "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v Test",
        "reg delete HKCU\\Software\\Test",
    ])
    def test_confirmation_required(self, command: str) -> None:
        """Commands with destructive patterns should require confirmation."""
        assert needs_confirmation(command), f"Command should need confirmation: {command}"

    @pytest.mark.parametrize("command", [
        "Get-Process",
        "echo hello",
        "notepad.exe",
        "dir C:\\Users",
        "whoami",
        "ipconfig /all",
    ])
    def test_no_confirmation_needed(self, command: str) -> None:
        """Read-only commands should not require confirmation."""
        assert not needs_confirmation(command), (
            f"Command should not need confirmation: {command}"
        )


# ── nl_to_powershell ───────────────────────────────────────────────────────

class TestNlToPowershell:
    """Tests for natural-language to PowerShell translation."""

    @pytest.mark.parametrize(("query", "expected_pattern"), [
        ("show RAM usage", "WorkingSet64"),
        ("check memory usage", "WorkingSet64"),
        ("how much ram is being used", "WorkingSet64"),
        ("cpu usage", "LoadPercentage"),
        ("check cpu temperature", "ThermalZoneTemperature"),
        ("disk space", "Get-PSDrive"),
        ("how much disk space is free", "Get-PSDrive"),
        ("running services", "Get-Service"),
        ("list running service", "Get-Service"),
        ("show open ports", "netstat"),
        ("open ports", "netstat"),
        ("startup programs", "Win32_StartupCommand"),
        ("current users", "query user"),
        ("logged in users", "query user"),
        ("wifi password", "netsh wlan show profile"),
        ("wifi networks", "netsh wlan show profiles"),
        ("flush dns", "Clear-DnsClientCache"),
        ("dns flush", "Clear-DnsClientCache"),
        ("installed apps", "Win32_Product"),
        ("installed software", "Win32_Product"),
        ("show my ip", "ipconfig"),
        ("ip info", "ipconfig"),
        ("system info", "systeminfo"),
        ("pc info", "systeminfo"),
        ("environment variables", "Get-ChildItem Env"),
        ("top processes", "Get-Process"),
        ("battery status", "powercfg"),
        ("battery health", "powercfg"),
        ("system uptime", "LastBootUpTime"),
        ("screen resolution", "System.Windows.Forms.Screen"),
        ("usb devices", "Get-PnpDevice"),
        ("network adapters", "Get-NetAdapter"),
        ("scheduled tasks", "Get-ScheduledTask"),
        ("event log errors", "Get-EventLog"),
        ("windows version", "Win32_OperatingSystem"),
        ("network latency", "Test-Connection"),
        ("gpu info", "Win32_VideoController"),
        ("gpu information", "Win32_VideoController"),
        ("user accounts", "Get-LocalUser"),
        ("windows features", "Get-WindowsOptionalFeature"),
        ("clipboard history", "Get-Clipboard"),
        ("power plan", "powercfg"),
        ("open task manager", "taskmgr"),
        ("open resource monitor", "resmon"),
        ("open event viewer", "eventvwr"),
        ("open services", "services.msc"),
    ])
    def test_nl_to_powershell(self, query: str, expected_pattern: str) -> None:
        """Natural language queries should translate to valid PowerShell."""
        result = nl_to_powershell(query)
        assert result is not None, f"No translation for: {query}"
        assert expected_pattern in result, (
            f"Expected '{expected_pattern}' in translation of '{query}': {result}"
        )

    @pytest.mark.parametrize("query", [
        "",
        "tell me a joke",
        "what is the meaning of life",
        "open chrome",
        "generate an image of a cat",
    ])
    def test_no_translation(self, query: str) -> None:
        """Non-system queries should return None."""
        assert nl_to_powershell(query) is None, (
            f"Query should not have a PS translation: {query}"
        )

    def test_case_insensitivity(self) -> None:
        """NL translation should be case-insensitive."""
        result_lower = nl_to_powershell("show ram usage")
        result_upper = nl_to_powershell("SHOW RAM USAGE")
        result_mixed = nl_to_powershell("Show RAM Usage")
        assert result_lower == result_upper, "Case should not matter"
        assert result_lower == result_mixed, "Case should not matter"


# ── diagnose_error ─────────────────────────────────────────────────────────

class TestDiagnoseError:
    """Tests for error diagnosis from command output."""

    @pytest.mark.parametrize(("output", "expected_keyword"), [
        ("Access is denied.", "permissions"),
        ("ERROR: access is denied", "permissions"),
        ("The system cannot find the file specified", "doesn't exist"),
        ("'python' is not recognized", "not in PATH"),
        ("Cannot find the path specified", "doesn't exist"),
        ("Out of memory", "low on RAM"),
        ("java.lang.OutOfMemoryError", "low on RAM"),
        ("Permission denied", "permissions"),
        ("The process cannot access the file", "locked by another process"),
        ("The network path was not found", "unavailable"),
        ("There is not enough space on the disk", "Free up space"),
        ("Disk is full", "Free up space"),
        ("Syntax error", "syntax"),
        ("syntax error: unexpected token", "syntax error"),
        ("File C:\\script.ps1 cannot be loaded because running scripts is disabled",
         "Enable scripts"),
        ("Execution policy", "execution policy"),
    ])
    def test_diagnose_error(self, output: str, expected_keyword: str) -> None:
        """Error output should produce a helpful diagnosis."""
        diagnosis = diagnose_error(output)
        assert diagnosis is not None, f"No diagnosis for: {output}"
        assert expected_keyword.lower() in diagnosis.lower(), (
            f"Diagnosis '{diagnosis}' should contain '{expected_keyword}'"
        )

    def test_no_match_returns_none(self) -> None:
        """Unknown errors should return None."""
        assert diagnose_error("Everything is fine.") is None
        assert diagnose_error("") is None
        assert diagnose_error("Operation completed successfully.") is None


# ── format_snapshot ────────────────────────────────────────────────────────

class TestFormatSnapshot:
    """Tests for system snapshot formatting."""

    def test_normal_snapshot(self) -> None:
        """A valid snapshot should format correctly."""
        snap = {
            "cpu_percent": 45.2,
            "ram_used_gb": 8.14,
            "ram_total_gb": 16.0,
            "ram_percent": 50.9,
            "disk_used_gb": 200.5,
            "disk_total_gb": 500.0,
            "disk_percent": 40.1,
            "uptime_hours": 72.5,
            "process_count": 245,
        }
        result = format_snapshot(snap)
        assert "CPU: 45.2%" in result
        assert "RAM: 8.14" in result
        assert "16.0 GB" in result
        assert "50.9%" in result
        assert "Disk (C:): 200.5" in result
        assert "Uptime: 72.5h" in result
        assert "245" in result

    def test_zero_values(self) -> None:
        """Snapshot with zero values should still format."""
        snap = {
            "cpu_percent": 0,
            "ram_used_gb": 0,
            "ram_total_gb": 0,
            "ram_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "disk_percent": 0,
            "uptime_hours": 0,
            "process_count": 0,
        }
        result = format_snapshot(snap)
        assert "CPU: 0%" in result

    def test_error_snapshot(self) -> None:
        """A snapshot with an error should show the error message."""
        snap = {"error": "MongoDB connection failed"}
        result = format_snapshot(snap)
        assert "unavailable" in result
        assert "MongoDB" in result


# ── generate_health_alerts ─────────────────────────────────────────────────

class TestGenerateHealthAlerts:
    """Tests for health alert generation from snapshots."""

    def test_no_alerts(self) -> None:
        """Normal values should produce no alerts."""
        snap = {
            "cpu_percent": 30,
            "ram_percent": 50,
            "disk_percent": 60,
        }
        assert generate_health_alerts(snap) == []

    def test_cpu_warning(self) -> None:
        """CPU > 75% should produce a warning."""
        snap = {"cpu_percent": 80, "ram_percent": 50, "disk_percent": 50}
        alerts = generate_health_alerts(snap)
        assert any(sev == "warning" and "CPU" in msg for sev, msg in alerts)

    def test_cpu_critical(self) -> None:
        """CPU > 90% should produce an error."""
        snap = {"cpu_percent": 95, "ram_percent": 50, "disk_percent": 50}
        alerts = generate_health_alerts(snap)
        assert any(sev == "error" and "CPU" in msg for sev, msg in alerts)

    def test_ram_warning(self) -> None:
        """RAM > 80% should produce a warning."""
        snap = {"cpu_percent": 30, "ram_percent": 85, "disk_percent": 50}
        alerts = generate_health_alerts(snap)
        assert any(sev == "warning" and "RAM" in msg for sev, msg in alerts)

    def test_ram_critical(self) -> None:
        """RAM > 90% should produce an error."""
        snap = {"cpu_percent": 30, "ram_percent": 95, "disk_percent": 50}
        alerts = generate_health_alerts(snap)
        assert any(sev == "error" and "RAM" in msg for sev, msg in alerts)

    def test_disk_warning(self) -> None:
        """Disk > 80% should produce a warning."""
        snap = {"cpu_percent": 30, "ram_percent": 50, "disk_percent": 85}
        alerts = generate_health_alerts(snap)
        assert any(sev == "warning" and "Disk" in msg for sev, msg in alerts)

    def test_disk_critical(self) -> None:
        """Disk > 90% should produce an error."""
        snap = {"cpu_percent": 30, "ram_percent": 50, "disk_percent": 95}
        alerts = generate_health_alerts(snap)
        assert any(sev == "error" and "Disk" in msg for sev, msg in alerts)

    def test_multiple_alerts(self) -> None:
        """Multiple issues should produce multiple alerts."""
        snap = {"cpu_percent": 92, "ram_percent": 88, "disk_percent": 96}
        alerts = generate_health_alerts(snap)
        severities = [sev for sev, _ in alerts]
        assert severities.count("error") >= 2
        assert severities.count("warning") >= 1

    def test_missing_keys(self) -> None:
        """Missing keys should not crash."""
        assert generate_health_alerts({}) == []
