from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyrad2 import client, dictionary
from pyrad2.constants import PacketType

from core.config import get_config
from core.config.models.radius import RemoteHost
from core.hotspot.wifi.repository import find_session_attrs_by_mac
from core.logging import get_logger


logger = get_logger('core.hotspot.wifi.coa')


@dataclass
class CoAResult:
    success: bool
    operation: str = 'coa'
    host: str | None = None
    code: int | None = None
    error_message: str | None = None


def _normalize_ip(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.strip()


def _dictionary_path() -> str:
    return str(Path(__file__).resolve().parents[3] / 'radius' / 'dictionary' / 'main')


def _normalize_port(raw: Any, default: int) -> int:
    if raw is None:
        return default
    return int(raw)


def _resolve_host(nas_target: dict[str, Any] | None) -> RemoteHost | None:
    config = get_config()
    hosts = [host for host in config.radius.hosts.values() if host.enabled]
    if not hosts:
        return None

    if not nas_target:
        return None

    nas_ip = _normalize_ip(nas_target.get('nas_ip'))
    radius_client_ip = _normalize_ip(nas_target.get('radius_client_ip'))

    for host in hosts:
        if nas_ip and host.address == nas_ip:
            return host

    for host in hosts:
        if radius_client_ip and host.address == radius_client_ip:
            return host

    return None


def _resolve_framed_ip(mac: str, nas_target: dict[str, Any] | None) -> str | None:
    if nas_target:
        framed_ip = _normalize_ip(nas_target.get('framed_ip'))
        if framed_ip:
            return framed_ip
    session_attrs = find_session_attrs_by_mac(mac)
    if not session_attrs:
        return None
    return _normalize_ip(session_attrs.get('last_ipv4_address'))


def send_group_switch(mac: str, target_group: str, nas_target: dict[str, Any] | None) -> CoAResult:
    host = _resolve_host(nas_target)
    if host is None:
        logger.warning(
            'CoA target host not found for NAS context',
            extra={'event': 'radius.coa.switch', 'mac': mac, 'target_group': target_group, 'nas_target': nas_target},
        )
        return CoAResult(success=False, error_message='CoA host not found')
    logger.info(
        'CoA target resolved',
        extra={
            'event': 'radius.coa.switch',
            'mac': mac,
            'target_group': target_group,
            'host': host.address,
            'nas_target': nas_target,
        },
    )
    framed_ip = _resolve_framed_ip(mac, nas_target)

    try:
        radius_dict = dictionary.Dictionary(_dictionary_path())
        authport = _normalize_port(getattr(host, 'authport', None), 1812)
        acctport = _normalize_port(getattr(host, 'acctport', None), 1813)
        coaport = _normalize_port(getattr(host, 'coaport', None), 3799)
        coa_client = client.Client(
            server=host.address,
            secret=host.secret,
            authport=authport,
            acctport=acctport,
            coaport=coaport,
            dict=radius_dict,
            retries=1,
            timeout=3,
        )
    except Exception as exc:
        logger.error(
            f'CoA client init failed host={host.address} error={type(exc).__name__}: {exc}',
            extra={
                'event': 'radius.coa.switch',
                'mac': mac,
                'target_group': target_group,
                'host': host.address,
                'error_type': type(exc).__name__,
            },
        )
        return CoAResult(success=False, operation='none', host=host.address, error_message=str(exc))

    try:
        packet = coa_client.CreateCoAPacket(code=PacketType.CoARequest)
        packet.AddAttribute('Calling-Station-Id', mac)
        packet.AddAttribute('User-Name', mac)
        packet.AddAttribute('MT-Group', target_group)
        if framed_ip:
            packet.AddAttribute('Framed-IP-Address', framed_ip)
        reply = coa_client.SendPacket(packet)
    except Exception as exc:
        logger.error(
            f'CoA group switch request failed host={host.address} error={type(exc).__name__}: {exc}',
            extra={
                'event': 'radius.coa.switch',
                'mac': mac,
                'target_group': target_group,
                'host': host.address,
                'error_type': type(exc).__name__,
            },
        )
        coa_error = str(exc)
    else:
        if reply.code == PacketType.CoAACK:
            logger.info(
                'CoA group switch ACK',
                extra={'event': 'radius.coa.switch', 'mac': mac, 'target_group': target_group, 'host': host.address, 'code': reply.code},
            )
            return CoAResult(success=True, operation='coa', host=host.address, code=reply.code)
        coa_error = f'CoA response code {reply.code}'
        logger.warning(
            'CoA group switch returned non-ACK',
            extra={'event': 'radius.coa.switch', 'mac': mac, 'target_group': target_group, 'host': host.address, 'code': reply.code},
        )

    try:
        disconnect_packet = coa_client.CreateCoAPacket(code=PacketType.DisconnectRequest)
        disconnect_packet.AddAttribute('Calling-Station-Id', mac)
        disconnect_packet.AddAttribute('User-Name', mac)
        if framed_ip:
            disconnect_packet.AddAttribute('Framed-IP-Address', framed_ip)
        disconnect_reply = coa_client.SendPacket(disconnect_packet)
    except Exception as exc:
        disconnect_error = str(exc)
        logger.warning(
            f'CoA disconnect fallback failed host={host.address} error={type(exc).__name__}: {exc}',
            extra={
                'event': 'radius.coa.switch',
                'mac': mac,
                'target_group': target_group,
                'host': host.address,
                'error_type': type(exc).__name__,
            },
        )
        return CoAResult(
            success=False,
            operation='disconnect_fallback',
            host=host.address,
            error_message=f'{coa_error}; disconnect: {disconnect_error}',
        )

    if disconnect_reply.code == PacketType.DisconnectACK:
        logger.info(
            'CoA disconnect fallback ACK',
            extra={'event': 'radius.coa.switch', 'mac': mac, 'target_group': target_group, 'host': host.address, 'code': disconnect_reply.code},
        )
        return CoAResult(success=True, operation='disconnect_fallback', host=host.address, code=disconnect_reply.code)

    logger.warning(
        'CoA disconnect fallback returned non-ACK',
        extra={'event': 'radius.coa.switch', 'mac': mac, 'target_group': target_group, 'host': host.address, 'code': disconnect_reply.code},
    )
    return CoAResult(
        success=False,
        operation='disconnect_fallback',
        host=host.address,
        code=disconnect_reply.code,
        error_message=f'{coa_error}; disconnect code {disconnect_reply.code}',
    )
