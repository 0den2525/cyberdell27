#!/usr/bin/env python3
"""Parser ringkas untuk backup konfigurasi Huawei (hw_ctree*.xml / TR-181).

Dipakai untuk mengaudit ulang fitur yang aktif di ONT/router Huawei tanpa perlu
membongkar XML secara manual.

Contoh:
    python3 audit/parse_ctree.py hw_ctreeHG.xml
    python3 audit/parse_ctree.py hw_ctreeHG.xml --enabled   # hanya daftar flag aktif
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET

ON = {"1", "enabled", "true", "yes", "on", "up"}
OFF = {"0", "disabled", "false", "no", "off", "down", ""}

ROOT: ET.Element  # diisi di main()


def status(value: str) -> str:
    v = (value or "").strip().lower()
    if v in ON:
        return "AKTIF"
    if v in OFF:
        return "mati"
    return value


def q(path: str, attr: str, default: str = "-") -> str:
    """Ambil atribut `attr` dari node di `path` (relatif terhadap root)."""
    node = ROOT.find(path) if path else ROOT
    if node is None:
        return default
    return node.attrib.get(attr, default)


def on(path: str, attr: str) -> str:
    """Status AKTIF/mati untuk atribut `attr` di node `path`."""
    return status(q(path, attr, ""))


def path_of(node: ET.Element) -> str:
    """Path lengkap node (butuh parent map; fallback ke nama tag)."""
    return node.tag


def mins_to_hhmm(value: str) -> str:
    """Ubah 'menit sejak 00:00' menjadi HH:MM (mis. 316 -> 05:16)."""
    try:
        total = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{total // 60:02d}:{total % 60:02d}"


def print_header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def section_device() -> None:
    print_header("1. IDENTITAS PERANGKAT")
    model = "-"
    for wps in ROOT.iter("WPS"):
        if wps.get("DeviceName"):
            model = wps.get("DeviceName")
            break
    xpon = "GPON" if q("X_HW_OmciInfo/XponMode", "mode") == "0" else "EPON"
    print(f"  Model (dari WPS)   : {model}")
    print(f"  Firmware           : {q('X_HW_ProductInfo', 'originalVersion')}")
    print(f"  Kustomisasi ISP    : {q('X_HW_ProductInfo', 'customInfo')} / "
          f"{q('X_HW_ProductInfo', 'customInfoDetail')}")
    print(f"  Alias perangkat    : {q('DeviceInfo', 'X_HW_DeviceAlias')}")
    print(f"  Mode uplink        : {xpon} (XponMode={q('X_HW_OmciInfo/XponMode', 'mode')}, "
          f"OMCI v{q('X_HW_OmciInfo/OmciVersion', 'version')})")
    print(f"  Pertama dipakai    : {q('DeviceInfo', 'FirstUseDate')}")
    print(f"  Reboot HW / SW     : {q('DeviceInfo', 'X_HW_TotalHWReboot')} / "
          f"{q('DeviceInfo', 'X_HW_TotalSWReboot')}")
    print(f"  Terakhir disimpan  : {q('X_HW_DataModel/X_HW_DataInfo', 'X_HW_LastSaveTime')} "
          f"({q('X_HW_DataModel/X_HW_DataInfo', 'X_HW_SaveTimes')} kali)")


def section_ssid() -> None:
    print_header("2. WI-FI / SSID")
    wc = ROOT.find("LANDevice/LANDeviceInstance/WLANConfiguration")
    if wc is None:
        print("  (tidak ada node WLANConfiguration)")
        return

    header = (f"{'ID':>3} {'iface':6} {'SSID':30} {'band':7} {'Sts':6} {'BC':4} "
              f"{'Keamanan':20} {'MaxKlien':8} {'WPS':4} {'Limit':8} {'VLAN'}")
    print(header)
    print("-" * len(header))
    for inst in wc.findall("WLANConfigurationInstance"):
        a = inst.attrib
        att_el = inst.find("X_HW_AttachConf")
        att = att_el.attrib if att_el is not None else {}
        wps = inst.find("WPS")
        sts = "UP" if a.get("Enable") == "1" else "down"
        bc = "ya" if a.get("SSIDAdvertisementEnabled") == "1" else "tidak"
        wps_st = "on" if (wps is not None and wps.get("Enable") == "1") else "off"
        sec = a.get("ModeEnabled") or "(mesh/backhaul)"
        print(f"{a.get('InstanceID', '?'):>3} {a.get('Name', ''):6} {a.get('SSID', '')[:30]:30} "
              f"{a.get('X_HW_RFBand', a.get('X_HW_Band', '-')):7} {sts:6} {bc:4} "
              f"{sec[:20]:20} {a.get('X_HW_AssociateNum', '-'):8} {wps_st:4} "
              f"{att.get('X_HW_UpRateLimit', '0')}/{att.get('X_HW_DownRateLimit', '0'):<6} "
              f"{a.get('X_HW_VLAN', '')}")
        if a.get("TotalPSKFailures", "0") not in ("0", ""):
            print(f"      ! kegagalan PSK tercatat: {a['TotalPSKFailures']}x")

    print("\n  Radio:")
    for radio in ROOT.findall("LANDevice/LANDeviceInstance/WiFi/Radio/RadioInstance"):
        print(f"    Radio {radio.get('InstanceID')} {radio.get('OperatingFrequencyBand'):7} "
              f"status={radio.get('Status'):5} enable={radio.get('Enable')} "
              f"mode-hemat={radio.get('X_HW_WallMode')}")


def section_wan() -> None:
    print_header("3. WAN")
    for inst in ROOT.findall("WANDevice/WANDeviceInstance/WANConnectionDevice/"
                             "WANConnectionDeviceInstance/WANIPConnection/WANIPConnectionInstance"):
        a = inst.attrib
        print(f"  [{a.get('InstanceID')}] {a.get('Name', '(tanpa nama)'):24} mode={a.get('ConnectionType'):12} "
              f"VLAN={a.get('X_HW_VLAN'):5} NAT={a.get('NATEnabled')} {on_path(inst)} "
              f"servis={a.get('X_HW_SERVICELIST')}")
    for inst in ROOT.findall("WANDevice/WANDeviceInstance/WANConnectionDevice/"
                             "WANConnectionDeviceInstance/WANPPPConnection/WANPPPConnectionInstance"):
        a = inst.attrib
        print(f"  [{a.get('InstanceID')}] {a.get('Name', '(tanpa nama)'):24} mode={a.get('TransportType'):12} "
              f"VLAN={a.get('X_HW_VLAN'):5} NAT={a.get('NATEnabled')} {on_path(inst)} "
              f"servis={a.get('X_HW_SERVICELIST')}")
        if a.get("Username"):
            print(f"        PPPoE user: {a['Username']} (password terenkripsi)")

    routes = ROOT.findall("Layer3Forwarding/X_HW_policy_route/X_HW_policy_routeInstance")
    if routes:
        print("\n  Policy route:")
        for r in routes:
            print(f"    {r.get('PhyPortName'):22} -> {r.get('WanName')}")

    nat = ROOT.find("X_HW_DataModel/NAT")
    if nat is not None:
        print(f"\n  Port mapping: {nat.get('PortMappingNumberOfEntries')} entri")


def on_path(node: ET.Element) -> str:
    return status(node.attrib.get("Enable", "")) if "Enable" in node.attrib else ""


def section_lan() -> None:
    print_header("4. LAN / DHCP / IPv6")
    base = "LANDevice/LANDeviceInstance/LANHostConfigManagement"
    print(f"  DHCP server        : {on(base, 'DHCPServerEnable')}")
    print(f"  Pool               : {q(base, 'MinAddress')} - {q(base, 'MaxAddress')} "
          f"(mask {q(base, 'SubnetMask')})")
    print(f"  Lease time         : {q(base, 'DHCPLeaseTime')} detik")
    print(f"  DNS ke klien       : {q(base, 'DNSServers') or q(base, 'X_HW_DNSList')}")
    print(f"  Static lease       : {q(base, 'DHCPStaticAddressNumberOfEntries')} entri")
    for ip in ROOT.findall(base + "/IPInterface/IPInterfaceInstance"):
        print(f"  Interface {ip.get('InstanceID')}      : {ip.get('IPInterfaceIPAddress')}"
              f"/{ip.get('IPInterfaceSubnetMask')} ({status(ip.get('Enable', ''))})")
    lan_ports = ROOT.findall("LANDevice/LANDeviceInstance/LANEthernetInterfaceConfig/"
                             "LANEthernetInterfaceConfigInstance")
    lan_up = sum(1 for e in lan_ports if e.get("Enable") == "1")
    print(f"  Port LAN aktif     : {lan_up}/{len(lan_ports)}")
    print(f"  IPv6 WAN           : IPv6Capable={q('X_HW_IPv6', 'IPv6Capable')}")
    print(f"  RA / DHCPv6 LAN    : {on('LANDevice/LANDeviceInstance/X_HW_RouterAdvertisement', 'Enable')}"
          f" / {on('LANDevice/LANDeviceInstance/X_HW_DHCPv6/Server', 'Enable')}")


def section_services() -> None:
    print_header("5. LAYANAN & KEAMANAN")
    acl = "X_HW_Security/AclServices"
    sec = "X_HW_Security"
    rows = [
        ("Telnet (CLI)", f"{on('UserInterface/X_HW_CLITelnetAccess', 'Access')} port "
                         f"{q('UserInterface/X_HW_CLITelnetAccess', 'TelnetPort')} | "
                         f"LAN:{q(acl, 'TELNETLanEnable')} WAN:{q(acl, 'TELNETWanEnable')} "
                         f"WiFi:{q(acl, 'TELNETWifiEnable')}"),
        ("SSH", f"LAN:{q(acl, 'SSHLanEnable')} WAN:{q(acl, 'SSHWanEnable')} "
                f"(port {q(acl, 'SSHPORT')})"),
        ("HTTP / HTTPS", f"LAN:{q(acl, 'HTTPLanEnable')}/{q(acl, 'HTTPSLanEnable')} "
                         f"WAN:{q(acl, 'HTTPWanEnable')}/{q(acl, 'HTTPSWanEnable')} "
                         f"WiFi:{q(acl, 'HTTPWifiEnable')} port {q(acl, 'HTTPPORT')}"),
        ("Remote access", on(acl + "/X_HW_RemoteAccess", "Enable")),
        ("TR-069 / CWMP", f"{on('ManagementServer', 'EnableCWMP')} (ACS: {q('ManagementServer', 'URL')})"),
        ("UPnP", f"main {on('X_HW_MainUPnP', 'Enable')} / slave {on('X_HW_SlvUPnP', 'Enable')}"),
        ("Firewall", f"{on(sec + '/Firewall', 'Enable')} tipe={q(sec + '/Firewall', 'Type')} "
                     f"level={q(sec, 'X_HW_FirewallLevel')}"),
        ("Proteksi port-scan", on(sec, "PortScanEnable")),
        ("Proteksi paket invalid", on(sec, "InvalidPacketDenyEnable")),
        ("Perlindungan DoS", on(sec, "X_HW_DosEnable")),
        ("Firewall IPv6", on(sec, "X_HW_IPv6FWDFireWallEnable")),
        ("Parental control", on(sec + "/ParentalCtrl", "Enable")),
        ("Filter MAC / URL", f"{q(sec, 'MacFilterNumberOfEntries')} / "
                             f"{q(sec, 'UrlFilterPolicy')}"),
        ("QoS", f"{on('QueueManagement', 'Enable')} "
                f"(klasifikasi {on('QueueManagement', 'X_HW_ClassificationEnable')})"),
        ("IGMP snooping/proxy", f"{on('Service/X_HW_IPTV', 'SnoopingEnable')} / "
                                f"{on('Service/X_HW_IPTV', 'ProxyEnable')}"),
        ("SMB/FTP/SFTP/DLNA",
         f"{on('Service/StorageService/StorageServiceInstance/NetworkServer', 'SMBEnable')} / "
         f"{on('X_HW_ServiceManage', 'FtpEnable')} / "
         f"{on('X_HW_SFTP/X_HW_SFTP_ServerInfo', 'SftpEnable')} / "
         f"{on('Service/X_HW_DmsService', 'Enable')}"),
        ("ALG", " ".join(f"{k[:-6]}:{v}" for k, v in
                         (ROOT.find('X_HW_ALG').attrib.items() if ROOT.find('X_HW_ALG') is not None
                          else []) if k.endswith("Enable"))),
        ("EasyMesh", f"{on('EasyMesh', 'Enable')} (roaming {q('EasyMesh', 'Roaming')})"),
        ("Auto reboot", f"{on('X_HW_AutoReboot', 'Enable')} tiap "
                        f"{q('X_HW_AutoReboot', 'RunningDays')} hari, jam "
                        f"{mins_to_hhmm(q('X_HW_AutoReboot', 'RebootStartTime'))}-"
                        f"{mins_to_hhmm(q('X_HW_AutoReboot', 'RebootEndTime'))}"),
        ("Akselerasi EAI", " ".join(
            f"{n.tag.replace('Acceleration', '')}:{n.get('Enable')}"
            for n in ROOT.findall("X_HW_EAIInfo/*") if n.get("Enable"))),
        ("Optimasi Wi-Fi", " ".join(
            f"{tag.replace('X_HW_', '')}:{on(tag, 'Enable')}"
            for tag in ("X_HW_SmartTopo", "X_HW_SmartCAT", "X_HW_CHL_SCAN",
                        "X_HW_OKC", "X_HW_LinkTurboInfo", "X_HW_BandWidthUpTo160"))),
        ("NTP / waktu", f"{on('Time', 'Enable')} ({q('Time', 'Status')}, TZ {q('Time', 'LocalTimeZone')})"),
    ]
    for name, value in rows:
        print(f"  {name:22}: {value}")

    print("\n  Akun web:")
    for u in ROOT.findall("UserInterface/X_HW_WebUserInfo/X_HW_WebUserInfoInstance"):
        level = "superadmin" if u.get("UserLevel") == "0" else "user"
        print(f"    {u.get('UserName'):10} level={u.get('UserLevel')} ({level}) "
              f"aktif={u.get('Enable')}")


def section_enabled() -> None:
    print_header("LAMPIRAN: SEMUA FLAG ENABLE YANG AKTIF")
    found: list[tuple[str, str]] = []

    def walk(node: ET.Element, path: str) -> None:
        path = f"{path}/{node.tag}"
        for key, value in node.attrib.items():
            if key.lower() in ("enable", "enabled") and (value or "").lower() in ON:
                found.append((path.replace("/InternetGatewayDevice", ""), value))
        for child in node:
            walk(child, path)

    walk(ROOT, "")
    for path, value in found:
        print(f"  {value:8} {path}")
    print(f"\n  Total: {len(found)} parameter aktif")


def main() -> int:
    global ROOT
    ap = argparse.ArgumentParser(description="Audit konfigurasi Huawei hw_ctree*.xml")
    ap.add_argument("file", help="path ke file XML backup")
    ap.add_argument("--enabled", action="store_true",
                    help="hanya tampilkan daftar flag enable yang aktif")
    args = ap.parse_args()

    try:
        ROOT = ET.parse(args.file).getroot()
    except (ET.ParseError, OSError) as exc:
        print(f"Gagal membaca {args.file}: {exc}", file=sys.stderr)
        return 1

    print(f"File : {args.file}")
    print(f"Root : {ROOT.tag} {ROOT.attrib}")
    if args.enabled:
        section_enabled()
        return 0

    section_device()
    section_ssid()
    section_wan()
    section_lan()
    section_services()
    section_enabled()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
