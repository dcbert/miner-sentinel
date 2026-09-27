"""LAN discovery for AxeOS HTTP and cgminer :4028 miners."""

from __future__ import annotations

import concurrent.futures
import ipaddress
import json
import logging
import socket
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _probe_axeos(ip: str, timeout: float = 0.8) -> dict[str, Any] | None:
    try:
        resp = requests.get(f'http://{ip}/api/system/info', timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
        hostname = data.get('hostname') or data.get('Hostname') or ip
        model = data.get('ASICModel') or data.get('boardVersion') or data.get('deviceModel') or 'AxeOS'
        return {
            'ip_address': ip,
            'make': 'bitaxe',
            'protocol': 'http_axeos',
            'port': 80,
            'suggested_name': str(hostname)[:100],
            'suggested_device_id': str(hostname).lower().replace(' ', '-')[:64] or ip.replace('.', '-'),
            'model': str(model)[:100] if model else None,
            'firmware': data.get('version') or data.get('axeOSVersion'),
        }
    except Exception:  # noqa: BLE001
        return None


def _probe_cgminer(ip: str, port: int = 4028, timeout: float = 0.8) -> dict[str, Any] | None:
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.send(json.dumps({'command': 'version'}).encode('utf-8'))
        raw = b''
        while True:
            try:
                chunk = sock.recv(2048)
                if not chunk:
                    break
                raw += chunk
            except socket.timeout:
                break
        text = raw.decode('utf-8', errors='ignore').replace('\x00', '').strip()
        if not text:
            return None
        parsed = json.loads(text)
        version = (parsed.get('VERSION') or [{}])[0] if isinstance(parsed, dict) else {}
        prod = version.get('PROD') or version.get('MODEL') or 'Avalon'
        return {
            'ip_address': ip,
            'make': 'avalon',
            'protocol': 'cgminer_tcp',
            'port': port,
            'suggested_name': str(prod)[:100],
            'suggested_device_id': str(prod).lower().replace(' ', '-')[:64] or ip.replace('.', '-'),
            'model': str(prod)[:100],
            'firmware': version.get('CGMiner') or version.get('API'),
        }
    except Exception:  # noqa: BLE001
        return None
    finally:
        if sock:
            sock.close()


def _hosts_from_cidr(cidr: str, limit: int = 254) -> list[str]:
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = []
    for host in net.hosts():
        hosts.append(str(host))
        if len(hosts) >= limit:
            break
    return hosts


def discover_lan(
    *,
    cidr: str | None = None,
    seed_ips: list[str] | None = None,
    max_workers: int = 32,
) -> list[dict[str, Any]]:
    """
    Scan a /24 (or provided CIDR) for AxeOS HTTP and cgminer TCP miners.

    If cidr is omitted, derive /24 from the first seed IP, else default 192.168.1.0/24.
    """
    hosts: list[str] = []
    if seed_ips:
        # Always probe seeds first
        for ip in seed_ips:
            if ip and ip not in hosts:
                hosts.append(ip)

    if cidr:
        for h in _hosts_from_cidr(cidr):
            if h not in hosts:
                hosts.append(h)
    elif seed_ips:
        try:
            first = ipaddress.ip_address(seed_ips[0])
            derived = str(ipaddress.ip_network(f'{first}/24', strict=False))
            for h in _hosts_from_cidr(derived):
                if h not in hosts:
                    hosts.append(h)
        except ValueError:
            pass
    else:
        hosts.extend(_hosts_from_cidr('192.168.1.0/24'))

    found: list[dict[str, Any]] = []
    seen_ips: set[str] = set()

    def probe(ip: str) -> dict[str, Any] | None:
        hit = _probe_axeos(ip) or _probe_cgminer(ip)
        return hit

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(probe, ip): ip for ip in hosts}
        for fut in concurrent.futures.as_completed(futures):
            try:
                result = fut.result()
            except Exception:  # noqa: BLE001
                continue
            if result and result['ip_address'] not in seen_ips:
                seen_ips.add(result['ip_address'])
                found.append(result)

    found.sort(key=lambda r: tuple(int(p) for p in r['ip_address'].split('.')))
    logger.info('LAN discovery found %s device(s) across %s host(s)', len(found), len(hosts))
    return found
