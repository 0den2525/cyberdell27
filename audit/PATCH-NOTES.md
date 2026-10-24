# Catatan Patch — Perbaikan Konfigurasi `hw_ctreeHG.xml`

Perangkat: **Huawei HG8145V5** · FW `V500R020C10SPC271A2307120359` · kustom `INATELKOM` · alias `DEllCore`

| Berkas | Keterangan |
|---|---|
| `audit/patch_ctree.py` | skrip patch (bisa `--dry-run`, tiap perbaikan bisa dimatikan sendiri) |
| `audit/out/hw_ctreeHG.hardened.xml` | **file hasil patch** — siap di-restore ke perangkat |
| `audit/out/hw_ctreeHG.hardened.diff` | diff 108 baris untuk verifikasi manual |
| `audit/parse_ctree.py` | skrip audit untuk cek ulang sebelum/sesudah |

## Metode patch (penting)

Skrip bekerja di **level teks**, bukan menulis ulang XML lewat parser. Alasannya:

* CRLF, urutan atribut, dan self-closing tag tetap **persis** seperti asli → parser firmware Huawei tidak kaget.
* Semua nilai terenkripsi `$2...` (password, PSK, kredensial PPPoE/ACS) **tidak disentuh** — kalau ikut ditulis ulang, perangkat bisa gagal mendekripsi dan Anda terkunci.

**Hasil verifikasi:** 13.557 atribut total → **hanya 21 yang berubah**, 13.536 sisanya identik byte-per-byte, termasuk **134 nilai `$2...` yang tidak berubah satu karakter pun**. Ukuran file tetap 381.219 byte, jumlah node XML tetap 2.202, CRLF tetap 2.474.

---

## 21 perubahan yang diterapkan

| # | Bug yang diperbaiki | Parameter | Sebelum | Sesudah |
|---|---|---|---|---|
| 1 | **Telnet (port 23) terbuka dari Wi-Fi** — siapa pun yang nyambung ke SSID mana pun bisa mencapai shell CLI | `X_HW_Security.AclServices.TELNETWifiEnable` | `1` | **`0`** |
| 2 | Tidak ada akses shell yang aman → SSH dibuka **hanya di LAN** (port 22) sebagai pengganti Telnet | `X_HW_Security.AclServices.SSHLanEnable` | `0` | **`1`** |
| 3 | **Tidak ada isolasi antar klien** → semua penyewa Wi-Fi satu jaringan datar, bisa saling mengakses — diterapkan ke 5 SSID sewa | `WLANConfiguration.{4,5,6,9,13}.X_HW_AttachConf.X_HW_IsolationEnable` | `0` | **`1`** |
| 4 | **802.11w / PMF mati** → frame manajemen tidak terproteksi (rawan deauth attack) — mode opsional, bukan wajib | `WLANConfiguration.{4,5,6,9,13}.X_IEEE80211wEnabled` | `0` | **`1`** |
| 5 | **Perlindungan DoS mati total** | `X_HW_Security.X_HW_DosEnable` | `0` | **`1`** |
| 6 | Filter SYN flood mati | `X_HW_Security.Dosfilter.SynFloodEn` | `0` | **`1`** |
| 7 | Filter serangan LAND mati | `X_HW_Security.Dosfilter.LandEn` | `0` | **`1`** |
| 8 | Filter Smurf mati | `X_HW_Security.Dosfilter.SmurfEn` | `0` | **`1`** |
| 9 | Filter WinNuke mati | `X_HW_Security.Dosfilter.WinnukeEn` | `0` | **`1`** |
| 10 | Filter ping sweep mati | `X_HW_Security.Dosfilter.PingSweepEn` | `0` | **`1`** |
| 11 | **Firewall IPv6 mati** | `X_HW_Security.X_HW_IPv6FWDFireWallEnable` | `0` | **`1`** |
| 12 | **Auto-reboot harian ~05:16–05:17** → koneksi putus tiap pagi | `X_HW_AutoReboot.Enable` | `1` | **`0`** |
| 13 | **Jadwal Wi-Fi mati 05:00–05:01 tiap hari** (SSID1) | `LANDevice.1.X_HW_WLANShutDownCtrl.ScheduleEnable` | `1` | **`0`** |

Catatan: baris 3, 4, 6–10 menyentuh beberapa objek sekaligus (5 SSID / 5 filter DoS) sehingga total 21 perubahan atribut.

### Status setelah patch (hasil `parse_ctree.py`)

```
Telnet (CLI)     : AKTIF port 23 | LAN:0 WAN:0 WiFi:0     ← tertutup dari semua sisi
SSH              : LAN:1 WAN:0 (port 22)                  ← akses shell aman, cuma dari LAN
Perlindungan DoS : AKTIF
Firewall IPv6    : AKTIF
Auto reboot      : mati (jam 05:16-05:17 tidak berlaku lagi)
```

---

## Yang sengaja TIDAK diubah

| Temuan | Mengapa tidak di-patch |
|---|---|
| **SSID `DiGiCOM.@Acut.net` tanpa password** (`BeaconType=Basic`) | PSK disimpan dalam format terenkripsi `$2...`; **tidak mungkin membuat password baru di luar perangkat**. SSID ini sudah `Enable=0`, jadi aman selama tidak dinyalakan. Perbaiki lewat web UI (hapus SSID ini, atau set WPA2 + password di UI). |
| **Rate limit per SSID = 0** | Butuh angka bandwidth paket Anda. Jalankan ulang dengan: `--rate-limit-up 5120 --rate-limit-down 20480` (kbps) bila sudah tahu. |
| **TR-069/ACS dimatikan** (`EnableCWMP=0`) | Bukan bug — ini mencegah ISP menimpa konfigurasi Anda. Biarkan mati kecuali Anda butuh bantuan remote ISP. |
| Parental control & daftar kata kunci | Pilihan Anda, bukan bug. |
| 187 reboot hardware / 40 reboot software, suhu Wi-Fi 71 °C | Gejala, bukan parameter konfigurasi. Kalau reboot masih sering setelah auto-reboot dimatikan, kemungkinan masalah daya/ventilasi/adaptor. |
| Kanal 2.4 GHz terkunci di kanal 6 | Mengubah kanal butuh uji lapangan; salah set bisa memperburuk interferensi. |
| SSID EasyMesh backhaul (ID 3 & 7) | Sengaja tidak disentuh — menyalakan isolasi/PMF di backhaul bisa memutus mesh. |

---

## Efek samping yang perlu Anda tahu

1. **Isolasi klien ON** → perangkat dalam SSID yang sama **tidak bisa saling mengakses** lagi (file sharing, Chromecast, printer jaringan, AirPrint antar-klien akan putus). Ini justru yang diinginkan untuk Wi-Fi sewaan, tapi kalau ada pelanggan yang butuh, matikan dengan `--no-isolation`.
2. **PMF = 1 (opsional)** → perangkat yang mendukung akan memakai proteksi; perangkat sangat lama yang tidak support tetap bisa connect. Kalau ada klien yang tiba-tiba gagal, ulangi dengan `--no-pmf`.
3. **Telnet mati dari semua sisi** → kalau terbiasa mengutak-atik lewat Telnet, pakai SSH dari LAN, atau jalankan ulang patch dengan `--keep-telnet`.
4. **SSH ON di LAN** → pastikan Anda memakai password yang kuat untuk user `Support` (level tertinggi) di menu web.
5. **DoS protection ON** → lalu lintas yang dianggap abnormal bisa diblokir. Kalau ada aplikasi yang aneh setelahnya, matikan dengan `--no-dos`.
6. **Auto-reboot OFF** → perangkat tidak lagi dibersihkan tiap pagi. Pantau saja; kalau mulai melambat, hidupkan lagi dengan `--keep-reboot`.

---

## Cara restore (baca sebelum menjalankan)

> ⚠️ **Risiko**: salah unggah konfigurasi bisa membuat perangkat tidak bisa diakses dan perlu reset fisik/factory. Lakukan hanya bila Anda punya akses fisik ke ONT dan masih ingat kredensial web-nya.

1. **Backup dulu** dari menu web ONT yang sekarang (System Tools → Configuration File → Backup) — simpan di luar folder repo.
2. Buka `http://192.168.100.1`, login sebagai **Support** (level tertinggi).
3. System Tools → Configuration File → **Restore / Load Configuration** → pilih `hw_ctreeHG.hardened.xml` → tunggu perangkat reboot sendiri (±2 menit).
4. Setelah hidup lagi, cek: SSID tetap tayang dengan password sama, PPPoE internet nyambung, lalu jalankan verifikasi di bawah.
5. **Gagal total?** Restore kembali file backup langkah 1. Masih gagal? Tekan tombol reset fisik ±10 detik lalu unggah backup Anda.

### Verifikasi setelah restore

```bash
python3 audit/parse_ctree.py hw_ctreeHG.hardened.xml
# atau bandingkan dengan kondisi awal:
python3 audit/parse_ctree.py hw_ctreeHG.xml --enabled | tail -3
python3 audit/parse_ctree.py hw_ctreeHG.hardened.xml --enabled | tail -3
```

Dari perangkat: coba `telnet 192.168.100.1 23` dari HP yang nyambung ke Wi-Fi → harus **gagal**; `ssh Support@192.168.100.1` dari kabel LAN → harus **berhasil**.

---

## Menyesuaikan patch

```bash
# lihat dulu tanpa menulis file
python3 audit/patch_ctree.py hw_ctreeHG.xml --dry-run

# contoh: tanpa isolasi klien, tanpa PMF, tapi pasang limit 20 Mbps down / 5 Mbps up
python3 audit/patch_ctree.py hw_ctreeHG.xml \
    --no-isolation --no-pmf \
    --rate-limit-down 20480 --rate-limit-up 5120 \
    -o audit/out/hw_ctreeHG.custom.xml

# hanya perbaiki jadwal reboot & telnet, sisanya biarkan
python3 audit/patch_ctree.py hw_ctreeHG.xml \
    --no-isolation --no-pmf --no-dos --no-ssh --no-ipv6-fw
```

Flag yang tersedia: `--no-isolation`, `--no-pmf`, `--no-dos`, `--no-ssh`,
`--no-ipv6-fw`, `--keep-telnet`, `--keep-reboot`, `--keep-wifi-schedule`,
`--tenant-ssids 4,5,6,9,13`, `--rate-limit-up N`, `--rate-limit-down N`, `--dry-run`.

---

## Keamanan berkas

`audit/out/` sudah dimasukkan ke `.gitignore`, jadi **tidak ikut ter-commit** ke Git.
Meski begitu, `hw_ctreeHG.hardened.xml` tetap berisi seluruh kredensial terenkripsi perangkat Anda (PPPoE, password `Admin`/`Support`, PSK semua SSID, kredensial ACS, password CLI `root`) dalam format `$2...`.

**Hapus folder `audit/out/` setelah selesai merestore konfigurasi.**
