#!/usr/bin/env python3
"""Patch hardening untuk konfigurasi Huawei (hw_ctree*.xml / TR-181).

PENTING
-------
* Skrip ini bekerja di level TEKS, bukan dengan parser XML. Tujuannya: hanya
  nilai atribut yang disebutkan saja yang berubah. CRLF, urutan atribut,
  self-closing tag, dan semua nilai terenkripsi ("$2...") dipertahankan
  persis seperti aslinya supaya perangkat tetap bisa mendekripsi kredensial.
* Setiap perubahan dicatat (nilai lama -> nilai baru) dan bisa di-dry-run
  dulu sebelum menulis file.
* File hasil patch HARAP di-restore ke perangkat yang sama. Nilai "$2..."
  terenkripsi dengan kunci perangkat.

Pemakaian
---------
    python3 audit/patch_ctree.py hw_ctreeHG.xml --dry-run
    python3 audit/patch_ctree.py hw_ctreeHG.xml -o audit/out/hw_ctreeHG.hardened.xml

Perbaikan yang diterapkan (lihat audit/hw_ctreeHG-audit.md):
    1. Tutup Telnet dari sisi Wi-Fi   (TELNETWifiEnable 1 -> 0)
    2. Buka SSH di LAN sebagai ganti  (SSHLanEnable     0 -> 1)
    3. Isolasi klien per SSID sewa    (X_HW_IsolationEnable 0 -> 1)
    4. Protected Management Frames    (X_IEEE80211wEnabled  0 -> 1, mode opsional)
    5. Perlindungan DoS               (X_HW_DosEnable 0 -> 1 + filter SynFlood/
                                       Land/Smurf/Winnuke/PingSweep)
    6. Firewall IPv6                  (X_HW_IPv6FWDFireWallEnable 0 -> 1)
    7. Matikan auto-reboot harian 05:16 (X_HW_AutoReboot Enable 1 -> 0)
    8. Matikan jadwal Wi-Fi mati 05:00  (X_HW_WLANShutDownCtrl ScheduleEnable 1 -> 0)
    9. [opsional] Rate limit per SSID sewa (--rate-limit-up / --rate-limit-down)
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

SSID_BLOCK_RE = re.compile(r'<WLANConfigurationInstance InstanceID="(\d+)"')
END_BLOCK = "</WLANConfiguration>"

# SSID penyewa/publik yang aktif (bukan SSID EasyMesh backhaul & bukan SSID mati)
DEFAULT_TENANT_SSIDS = (4, 5, 6, 9, 13)


@dataclass
class Change:
    target: str
    attr: str
    old: str
    new: str

    def render(self) -> str:
        return f"{self.target:52} {self.attr:26} {self.old:>10} -> {self.new}"


@dataclass
class Result:
    changes: list[Change] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def set_attr(text: str, attr: str, new: str, how_many: int = 0) -> tuple[str, str | None]:
    """Ganti nilai atribut `attr` dalam `text`.

    how_many=0 -> semua kemunculan; selainnya -> sebanyak itu.
    Mengembalikan (teks_baru, nilai_lama atau None bila tidak ketemu).
    """
    pattern = re.compile(r"\b" + re.escape(attr) + r'="([^"]*)"')
    old_values = pattern.findall(text)
    if not old_values:
        return text, None
    if how_many:
        text, n = pattern.subn(f'{attr}="{new}"', text, count=how_many)
    else:
        text, n = pattern.subn(f'{attr}="{new}"', text)
    return text, old_values[0]


def split_ssid_blocks(text: str) -> list[tuple[int, int, int]]:
    """Potong dokumen menjadi blok per <WLANConfigurationInstance>.

    Mengembalikan [(instance_id, start, end), ...] dengan urutan kemunculan.
    """
    starts = [(int(m.group(1)), m.start()) for m in SSID_BLOCK_RE.finditer(text)]
    if not starts:
        return []
    end_of_parent = text.find(END_BLOCK)
    if end_of_parent == -1:
        end_of_parent = len(text)

    blocks: list[tuple[int, int, int]] = []
    for i, (inst_id, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else end_of_parent
        blocks.append((inst_id, start, end))
    return blocks


def ssid_label(text: str, block: tuple[int, int, int]) -> str:
    inst_id, start, end = block
    chunk = text[start:end]
    m = re.search(r'\bSSID="([^"]*)"', chunk)
    name = m.group(1) if m else "(tanpa nama)"
    return f"WLANConfiguration.{inst_id} [{name[:22]}]"


def apply_ssid_fixes(text: str, args, res: Result) -> str:
    blocks = split_ssid_blocks(text)
    if not blocks:
        res.skipped.append("Tidak ada blok WLANConfigurationInstance — lewati perbaikan Wi-Fi.")
        return text

    # rebuild dari belakang supaya offset blok lain tidak bergeser
    for inst_id, start, end in reversed(blocks):
        if inst_id not in args.tenant_ssids:
            continue
        label = ssid_label(text, (inst_id, start, end))
        chunk = text[start:end]

        if not args.no_isolation:
            chunk, old = set_attr(chunk, "X_HW_IsolationEnable", "1")
            if old is not None and old != "1":
                res.changes.append(Change(label, "X_HW_IsolationEnable", old, "1"))

        if not args.no_pmf:
            chunk, old = set_attr(chunk, "X_IEEE80211wEnabled", "1")
            if old is not None and old != "1":
                res.changes.append(Change(label, "X_IEEE80211wEnabled", old, "1"))

        if args.rate_limit_up:
            chunk, old = set_attr(chunk, "X_HW_UpRateLimit", str(args.rate_limit_up))
            if old is not None and old != str(args.rate_limit_up):
                res.changes.append(Change(label, "X_HW_UpRateLimit", old, str(args.rate_limit_up)))

        if args.rate_limit_down:
            chunk, old = set_attr(chunk, "X_HW_DownRateLimit", str(args.rate_limit_down))
            if old is not None and old != str(args.rate_limit_down):
                res.changes.append(Change(label, "X_HW_DownRateLimit", old, str(args.rate_limit_down)))

        text = text[:start] + chunk + text[end:]

    return text


def apply_global_fixes(text: str, args, res: Result) -> str:
    # helper untuk atribut yang hanya muncul sekali di seluruh dokumen
    def once(attr: str, new: str, label: str) -> None:
        nonlocal text
        count = len(re.findall(r"\b" + re.escape(attr) + r'="', text))
        if count != 1:
            res.skipped.append(
                f"{attr}: ditemukan {count}x (harus tepat 1x) — dilewati demi keamanan.")
            return
        chunk, old = set_attr(text, attr, new, how_many=1)
        if old is not None and old != new:
            text = chunk
            res.changes.append(Change(label, attr, old, new))

    # helper untuk atribut di dalam elemen tertentu (nama atributnya umum,
    # mis. "Enable" yang muncul ratusan kali di dokumen)
    def once_in_tag(tag: str, attr: str, new: str, label: str) -> None:
        nonlocal text
        matches = list(re.finditer(r"<" + re.escape(tag) + r"\b[^>]*>", text))
        if len(matches) != 1:
            res.skipped.append(
                f"<{tag}>: ditemukan {len(matches)}x (harus tepat 1x) — dilewati.")
            return
        m = matches[0]
        chunk, old = set_attr(m.group(0), attr, new, how_many=1)
        if old is None:
            res.skipped.append(f"<{tag}>: atribut {attr} tidak ada — dilewati.")
            return
        if old == new:
            return
        text = text[:m.start()] + chunk + text[m.end():]
        res.changes.append(Change(label, attr, old, new))

    # 1. Telnet: tutup akses dari Wi-Fi
    if not args.keep_telnet:
        once("TELNETWifiEnable", "0", "X_HW_Security.AclServices")
    # 2. SSH: buka hanya di LAN (pengganti telnet yang aman)
    if not args.no_ssh:
        once("SSHLanEnable", "1", "X_HW_Security.AclServices")
    # 5. DoS protection
    if not args.no_dos:
        once("X_HW_DosEnable", "1", "X_HW_Security")
        for attr in ("SynFloodEn", "LandEn", "SmurfEn", "WinnukeEn", "PingSweepEn"):
            once(attr, "1", "X_HW_Security.Dosfilter")
    # 6. Firewall IPv6
    if not args.no_ipv6_fw:
        once("X_HW_IPv6FWDFireWallEnable", "1", "X_HW_Security")
    # 7. Auto reboot harian (atribut "Enable" di elemen <X_HW_AutoReboot>)
    if not args.keep_reboot:
        once_in_tag("X_HW_AutoReboot", "Enable", "0", "X_HW_AutoReboot")
    # 8. Jadwal Wi-Fi mati tiap hari
    if not args.keep_wifi_schedule:
        once_in_tag("X_HW_WLANShutDownCtrl", "ScheduleEnable", "0",
                    "LANDevice.X_HW_WLANShutDownCtrl")

    return text


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Patch hardening konfigurasi Huawei hw_ctree*.xml",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="file XML asli (backup hw_ctree*.xml)")
    ap.add_argument("-o", "--out", help="file hasil patch (default: <nama>.hardened.xml)")
    ap.add_argument("--dry-run", action="store_true",
                    help="tampilkan rencana perubahan tanpa menulis file")
    ap.add_argument("--tenant-ssids", default=",".join(map(str, DEFAULT_TENANT_SSIDS)),
                    help="InstanceID SSID penyewa yang dipatch (default: 4,5,6,9,13)")
    ap.add_argument("--no-isolation", action="store_true", help="jangan aktifkan AP isolation")
    ap.add_argument("--no-pmf", action="store_true", help="jangan aktifkan 802.11w/PMF")
    ap.add_argument("--no-dos", action="store_true", help="jangan aktifkan DoS protection")
    ap.add_argument("--no-ssh", action="store_true", help="jangan buka SSH di LAN")
    ap.add_argument("--no-ipv6-fw", action="store_true", help="jangan aktifkan firewall IPv6")
    ap.add_argument("--keep-telnet", action="store_true", help="biarkan Telnet dari Wi-Fi")
    ap.add_argument("--keep-reboot", action="store_true", help="biarkan auto-reboot harian")
    ap.add_argument("--keep-wifi-schedule", action="store_true",
                    help="biarkan jadwal Wi-Fi mati harian")
    ap.add_argument("--rate-limit-up", type=int, default=0,
                    help="batas upload per SSID penyewa (kbps), 0 = tidak diubah")
    ap.add_argument("--rate-limit-down", type=int, default=0,
                    help="batas download per SSID penyewa (kbps), 0 = tidak diubah")
    args = ap.parse_args()

    try:
        args.tenant_ssids = {int(x) for x in args.tenant_ssids.split(",") if x.strip()}
    except ValueError:
        print("--tenant-ssids harus berupa angka dipisah koma", file=sys.stderr)
        return 1

    # newline="" -> CRLF asli tidak diubah
    with open(args.file, encoding="utf-8", newline="") as fh:
        original = fh.read()

    res = Result()
    patched = apply_global_fixes(original, args, res)
    patched = apply_ssid_fixes(patched, args, res)

    # urutkan catatan supaya rapi (SSID kecil ke besar)
    res.changes.sort(key=lambda c: c.target)

    print("=" * 96)
    print("RENCANA PERUBAHAN - patch hardening hw_ctree*.xml")
    print("=" * 96)
    if res.changes:
        for c in res.changes:
            print("  " + c.render())
    else:
        print("  (tidak ada perubahan — konfigurasi sudah sesuai target)")
    if res.skipped:
        print("\nDilewati:")
        for s in res.skipped:
            print(f"  ! {s}")
    print(f"\nTotal: {len(res.changes)} perubahan")

    if args.dry_run:
        print("\n[--dry-run] tidak ada file yang ditulis.")
        return 0

    out = args.out or (args.file.rsplit(".", 1)[0] + ".hardened.xml")

    # validasi: pastikan hasil tetap well-formed XML & tidak ada node yang hilang
    try:
        before = ET.fromstring(original)
        after = ET.fromstring(patched)
    except ET.ParseError as exc:
        print(f"GAGAL: hasil patch tidak valid sebagai XML ({exc}). File tidak ditulis.",
              file=sys.stderr)
        return 2

    def count_nodes(node: ET.Element) -> int:
        return 1 + sum(count_nodes(c) for c in node)

    n_before, n_after = count_nodes(before), count_nodes(after)
    if n_before != n_after:
        print(f"GAGAL: jumlah node berubah ({n_before} -> {n_after}). File tidak ditulis.",
              file=sys.stderr)
        return 2

    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(patched)

    print(f"\nOK: {len(patched)} karakter -> {out}")
    print(f"    node XML: {n_after} (sama dengan asli) | baris: "
          f"{patched.count(chr(10)) + 1}")

    # sanity check: nilai terenkripsi tidak boleh berubah
    enc_before = len(re.findall(r'"\$2', original))
    enc_after = len(re.findall(r'"\$2', patched))
    print(f"    nilai terenkripsi $2... : {enc_before} -> {enc_after} "
          f"({'aman' if enc_before == enc_after else 'BERUBAH - JANGAN DIPAKAI!'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
