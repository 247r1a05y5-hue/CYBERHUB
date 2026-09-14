"""Deterministic mock threat intelligence provider."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from app.intel.base import ThreatIntelProvider, ThreatIntelResult


class MockThreatIntelProvider(ThreatIntelProvider):
    """
    Deterministic Threat Intel Provider for test & dev environments.
    Maintains a list of synthetic known-bad indicators.
    """

    KNOWN_BAD = {
        "ip_address": {
            "198.51.100.1": ("C2 Server - Cobalt Strike", 95.0, ["c2", "trojan"]),
            "203.0.113.50": ("Known Scanner / Brute Force", 75.0, ["scanner", "botnet"]),
            "192.0.2.100": ("Phishing Host", 85.0, ["phishing"]),
        },
        "domain": {
            "malicious-payload-cdn.xyz": ("Malware Distribution", 98.0, ["malware", "downloader"]),
            "secure-login-update-verify.com": ("Phishing Credential Harvester", 92.0, ["phishing", "credential_harvesting"]),
            "evil-corp-c2.duckdns.org": ("Dynamic DNS C2", 90.0, ["c2"]),
        },
        "file_hash": {
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": ("Empty test hash", 0.0, ["benign"]),
            "44d88612fea8a8f36de82e1278abb02f": ("EICAR Test String Hash", 99.0, ["test_virus", "eicar"]),
            "d41d8cd98f00b204e9800998ecf8427e": ("Empty MD5", 0.0, ["benign"]),
            "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f": ("Known Ransomware Sample", 100.0, ["ransomware", "lockbit"]),
        },
        "url": {
            "http://malicious-payload-cdn.xyz/drop.exe": ("Direct Malware Download", 99.0, ["malware_url"]),
            "https://secure-login-update-verify.com/login.php": ("Phishing Landing Page", 95.0, ["phishing_url"]),
        }
    }

    @property
    def name(self) -> str:
        return "MockThreatIntel"

    async def lookup(self, indicator_type: str, value: str) -> Optional[ThreatIntelResult]:
        type_table = self.KNOWN_BAD.get(indicator_type, {})
        entry = type_table.get(value.lower().strip())

        if entry:
            desc, score, types = entry
            return ThreatIntelResult(
                provider=self.name,
                indicator_type=indicator_type,
                value=value,
                is_malicious=score >= 50.0,
                reputation_score=score,
                confidence=0.95,
                threat_types=types,
                tags=["mock_intel", "demo"],
                first_seen=datetime(2026, 1, 1, tzinfo=timezone.utc),
                last_seen=datetime.now(timezone.utc),
                raw_response={"matched_entry": desc, "score": score},
            )

        # If not known bad, return clean response
        return ThreatIntelResult(
            provider=self.name,
            indicator_type=indicator_type,
            value=value,
            is_malicious=False,
            reputation_score=5.0,
            confidence=0.60,
            threat_types=[],
            tags=["clean"],
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            raw_response={"status": "not_in_known_threat_database"},
        )

    async def is_available(self) -> bool:
        return True
