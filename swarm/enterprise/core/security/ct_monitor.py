"""
Certificate Transparency (CT) Monitoring.
Monitors CT logs for certificates issued for your domains.
Uses crt.sh API for certificate lookup.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class CTCertificate:
    """A certificate found in CT logs."""
    issuer_ca: str = ""
    common_name: str = ""
    name_value: str = ""  # SAN entries
    not_before: str = ""
    not_after: str = ""
    serial_number: str = ""
    entry_timestamp: str = ""
    id: str = ""
    
    def is_recent(self, days: int = 7) -> bool:
        """Check if certificate was issued recently."""
        try:
            if self.entry_timestamp:
                ct_time = datetime.fromisoformat(self.entry_timestamp.replace('Z', '+00:00'))
                return datetime.now(timezone.utc) - ct_time < timedelta(days=days)
        except Exception:
            pass
        return False


@dataclass 
class CTAlert:
    """Alert for suspicious CT log entry."""
    alert_id: str = ""
    domain: str = ""
    certificate: Optional[CTCertificate] = None
    reason: str = ""
    severity: str = "warning"  # info, warning, critical
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CertificateTransparencyMonitor:
    """Monitors Certificate Transparency logs for unauthorized certificates."""
    
    CRT_SH_API = "https://crt.sh/?q={domain}&output=json&exclude=expired"
    
    def __init__(
        self,
        domains_to_monitor: List[str],
        check_interval_hours: int = 6,
        alert_callback: Optional[Callable[[CTAlert], None]] = None,
    ):
        self.domains = domains_to_monitor
        self.check_interval = check_interval_hours * 3600  # seconds
        self.alert_callback = alert_callback
        self._known_certs: Dict[str, set] = {d: set() for d in self.domains}
        self._alerts: List[CTAlert] = []
        self._running = False
    
    async def check_domain(self, domain: str) -> List[CTCertificate]:
        """Check CT logs for a specific domain."""
        import aiohttp
        
        url = self.CRT_SH_API.format(domain=domain)
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        certs = []
                        
                        for entry in data[:50]:  # Limit results
                            cert = CTCertificate(
                                issuer_ca=entry.get("issuer_name", ""),
                                common_name=entry.get("common_name", ""),
                                name_value=entry.get("name_value", ""),
                                not_before=entry.get("not_before", ""),
                                not_after=entry.get("not_after", ""),
                                serial_number=entry.get("serial_number", ""),
                                entry_timestamp=entry.get("entry_timestamp", ""),
                                id=str(entry.get("id", "")),
                            )
                            certs.append(cert)
                        
                        return certs
                    else:
                        logger.warning(f"CT check failed for {domain}: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"CT check error for {domain}: {e}")
        
        return []
    
    async def monitor_once(self) -> List[CTAlert]:
        """Run one monitoring cycle across all domains."""
        alerts = []
        
        for domain in self.domains:
            certs = await self.check_domain(domain)
            
            for cert in certs:
                cert_key = f"{cert.serial_number}:{cert.common_name}"
                
                # Check if this is a new certificate
                if cert_key not in self._known_certs[domain]:
                    self._known_certs[domain].add(cert_key)
                    
                    # Check if it's recent and potentially suspicious
                    if cert.is_recent(days=7):
                        alert = CTAlert(
                            alert_id=f"ct-{domain}-{cert.serial_number}",
                            domain=domain,
                            certificate=cert,
                            reason="New certificate issued in last 7 days",
                            severity="info",
                        )
                        alerts.append(alert)
                        
                        if self.alert_callback:
                            try:
                                self.alert_callback(alert)
                            except Exception as e:
                                logger.error(f"Alert callback failed: {e}")
        
        self._alerts.extend(alerts)
        return alerts
    
    async def start_monitoring(self):
        """Start continuous monitoring loop."""
        self._running = True
        
        while self._running:
            await self.monitor_once()
            await asyncio.sleep(min(self.check_interval, 3600))  # Cap at 1hr for testing
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self._running = False
    
    def get_alerts(
        self,
        domain: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[CTAlert]:
        """Get stored alerts with filters."""
        alerts = self._alerts
        
        if domain:
            alerts = [a for a in alerts if a.domain == domain]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts[-limit:]
    
    @staticmethod
    def create_default_monitor(
        domains: List[str],
        alert_callback: Optional[Callable] = None,
    ) -> "CertificateTransparencyMonitor":
        """Create a CT monitor with default settings."""
        return CertificateTransparencyMonitor(
            domains_to_monitor=domains,
            check_interval_hours=6,
            alert_callback=alert_callback,
        )
