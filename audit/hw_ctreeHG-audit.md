# Audit Fitur Aktif — `hw_ctreeHG.xml`

> ✅ **Perbaikan tersedia.** Temuan di laporan ini sudah dibuatkan patch-nya:
> `audit/patch_ctree.py` (skrip) → `audit/out/hw_ctreeHG.hardened.xml` (21 perubahan).
> Penjelasan tiap perubahan, efek samping, dan cara restore: **[audit/PATCH-NOTES.md](PATCH-NOTES.md)**.

**Sumber data:** backup konfigurasi `hw_ctreeHG.xml` (381 KB, 2.474 baris, 2.202 elemen XML, 406 tag unik)
**Format:** Huawei `InternetGatewayDevice` TR-181 (cwmp/tr-181-2-11-0), `DBEncrypt="1"` → semua password/PSK tersimpan terenkripsi (`$2...`)
**Tanggal audit:** 2026-10-24 (WIB)

---

## 1. Identitas perangkat

| Item | Nilai |
|---|---|
| Model (dari `WPS.DeviceName`) | **Huawei HG8145V5** (GPON ONT, Wi-Fi 6 / AX) |
| Firmware | `V500R020C10SPC271A2307120359` (`currentVersion V500R020`) |
| Kustomisasi ISP | `INATELKOM` / `inatelkom` |
| Alias perangkat | **DEllCore** |
| Mode uplink | GPON (`XponMode=0`, `OMCI v2`, `X_HW_UpPortMode=4`), status optik **Up** |
| Data model | TR-181-2-11-0 — fitur `VOICE,WIFI,Router` |
| Arsitektur CPU | arm |
| Pertama dipakai | 2026-08-07 19:33 / online pertama 2026-08-08 02:33 |
| Konfigurasi terakhir disimpan | 2026-10-24 22:10:41 (`SaveTimes: 1479`, via `TR-069\|WEB`) |
| Jumlah reboot | **187× hardware, 40× software** |
| Suhu puncak tercatat | OPTIC 48 °C · CPU **64 °C** · Wi-Fi **71 °C** |

---

## 2. Ringkasan: fitur yang SUDAH AKTIF MAKSIMAL

### ✅ Sudah menyala penuh ("maksimal")

| Kategori | Fitur | Status | Path kunci |
|---|---|---|---|
| **Wi-Fi radio** | Radio 2.4 GHz **Up** + Radio 5 GHz **Up** | ON | `LANDevice.1.WiFi.Radio.{1,2}.Enable=1` |
| **Wi-Fi daya** | TX Power **100 %** di semua 9 SSID | MAX | `TransmitPower=100`, `X_HW_PowerValue=100` |
| **Kapasitas SSID** | 9 SSID terkonfigurasi, **7 aktif** (slot tersedia s/d SSID13) | ON | `WLANConfiguration` (9 instance) |
| **Lebar kanal 5 GHz** | `X_HW_HT20=3` (80 MHz) + **BandWidthUpTo160 ON** (160 MHz) | MAX | `X_HW_BandWidthUpTo160.Enable=1` |
| **2.4 GHz 256-QAM** | ON di semua SSID user | ON | `X_HW_2G256QAM=1` |
| **Band steering** | ON (cycle 30 s) | ON | `WiFi.X_HW_GlobalConfig.BandSteeringPolicy=1` |
| **EasyMesh / roaming** | ON, role Auto, roaming ON, 2 backhaul SSID tersembunyi aktif | ON | `EasyMesh.Enable=1`, `Roaming=1` |
| **OKC (fast roaming)** | ON | ON | `X_HW_OKC.Enable=1` |
| **SmartTopo / SmartCAT / CHL_SCAN** | semuanya ON (topologi & pemilihan kanal otomatis) | ON | masing-masing `.Enable=1` |
| **LinkTurbo** | ON | ON | `X_HW_LinkTurboInfo.Enable=1` |
| **Akselerasi aplikasi (EAI)** | **Game, Ping, Edu, Office, Video — 5/5 ON, status `on`** | MAX | `X_HW_EAIInfo.*.Enable=1` |
| **MU-MIMO / TxBF / Airtime Fairness / Agregasi paket / TWT** | ON | MAX | `X_HW_AttachConf.*` |
| **QoS** | QueueManagement ON + klasifikasi ON | ON | `QueueManagement.Enable=1`, `X_HW_QosEnable=1` |
| **Firewall** | Stateful, ON, level `Custom`, general level 4 | ON | `X_HW_Security.Firewall.Enable=1` |
| **Anti port-scan & paket invalid** | ON | ON | `PortScanEnable=1`, `InvalidPacketDenyEnable=1` |
| **Batas sesi** | 4000 sesi | ON | `UsrSessionLimit.Enable=1` |
| **Kontrol WAN global** | ON (480) | ON | `X_HW_WANGlobalControl.Enable=1` |
| **Parental control + filter URL** | ON, daftar kata kunci diblok ke **semua MAC** | ON | `ParentalCtrl.Enable=1`, MAC `FF:FF:FF:FF:FF:FF` |
| **UPnP** | Main **dan** Slave ON | ON | `X_HW_MainUPnP.Enable=1`, `X_HW_SlvUPnP.Enable=1` |
| **ALG** | TFTP, H323, SIP, RTSP, L2TP, IPSec, PPTP, FTP — semua ON (RTCP off) | MAX | `X_HW_ALG.*Enable=1` |
| **IGMP Snooping** | ON | ON | `Service.X_HW_IPTV.SnoopingEnable=1` |
| **DNS** | Cache + DNS server/relay ON | ON | `X_HW_DNS.CacheEnable=1`, `DnsServerEnable=1` |
| **NTP / waktu** | ON & **tersinkron**, TZ +07:00 (Jakarta), server he.net | ON | `Time.Enable=1`, `Status=Synchronized` |
| **Akses web lokal** | HTTP:80 LAN+Wi-Fi ON, HTTPS:443 LAN ON, sertifikat SSL ON | ON | `AclServices.HTTPLanEnable=1`, `X_HW_WebSslInfo.Enable=1` |
| **SAMBA (ACL)** | diizinkan di LAN | ON | `SamBaLanEnable=1` |
| **Content Sharing / Storage** | ON | ON | `ContentSharing.Enable=1`, `StorageServiceInstance.Enable=1` |
| **Monitoring PON** | ON (interval 900 s) | ON | `X_HW_PonQualityMonitor.Enable=1` |
| **Loopback detection LAN** | ON | ON | `X_HW_LoopbackDetection.LoopbackEnable=1` |
| **Auto reboot** | ON — tiap 1 hari, jendela **05:16–05:17** | ON | `X_HW_AutoReboot` `RunningDays=1`, `316/317` |
| **Jadwal mati Wi-Fi** | ON — **05:00–05:01 setiap hari** (berlaku SSID index 1) | ON | `X_HW_WLANShutDownCtrl` |
| **Kontainer LXC** | ExecEnv ON, `kernelapp` (netopen cplugin 22.1.87) **ACTIVE**, AutoStart | ON | `SoftwareModules.ExecEnv.1` |
| **Deteksi brute-force PSK** | ON | ON | `X_HW_PskMassiveDetect.Enable=1` |
| **Alarm sertifikat keamanan** | ON | ON | `X_HW_DataModel.SecurityCertAlarm.Enable=1` |

### ⚠️ Menyala, tapi perlu perhatian

| Fitur | Status | Catatan |
|---|---|---|
| **Telnet CLI** | `X_HW_CLITelnetAccess.Access=1` port **23** | `TELNETWifiEnable=1` → **telnet bisa diakses dari Wi-Fi** (LAN/WAN = 0) |
| **Firewall level** | `Custom` / general level 4 | Bukan level tertinggi; aturan kustom kosong |
| **Profil suara / VoIP** | `Enable=Enabled` | Tapi semua server SIP/Proxy/Registrar **kosong** → VoIP tidak terhubung ke mana pun |
| **Wi-Fi 2.4 GHz channel** | Manual kanal **6** di semua SSID (auto OFF) | Potensi kongesti satu kanal |
| **Profil SIP/H248** | Ada & lengkap | Tidak dipakai (tidak ada WAN dengan `SERVICELIST=VOICE` aktif selain TR069_VOIP) |

### ❌ Belum aktif (masih bisa dinaikkan)

DoS protection (`X_HW_DosEnable=0`) · SSH LAN/WAN (`0`) · SFTP (`0`) · FTP LAN/WAN (`0`) · Server SMB aktif (`SMBEnable=0`) · DLNA/DMS (`0`) · USB (`0`) · IPv6 WAN (`IPv6Capable=0`) · Firewall IPv6 (`0`) · TR-069 CWMP (`EnableCWMP=0`) · Remote access HTTP/HTTPS (`0`) · WPS (semua SSID `0`) · 802.11w/PMF (`0`) · Port mapping / Port trigger / DMZ (0 entri) · Static DHCP lease (0) · MAC filter (0) · URL filter (0) · Traffic control/shaping (`0`) · DDNS · VPN server · BulkData · eMDI · Portal captive · Audit log · Mobile backup · Printer sharing · CloudVR.

---

## 3. Detail Wi-Fi (9 SSID)

| ID | Iface | SSID | Band | Aktif | Broadcast | Keamanan | **Maks. klien** | Limit up/down | Isolasi |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ath0 | `SAMSUNG` | 2.4G | ❌ Off | ✗ | WPA/WPA2-Personal | 32 | 0/0 | ✗ |
| 2 | ath1 | `DiGiCOM.@Acut.net` | 2.4G | ❌ Off | ✓ | **None (OPEN)** | 3 | 0/0 | ✗ |
| 3 | ath7 | `Easymesh_Backhaul26709531` | 2.4G | ✅ | ✗ tersembunyi | WPA/WPA2 | 32 | 0/0 | ✗ |
| 4 | ath3 | `Alika Caffe` | 2.4G | ✅ | ✓ | WPA/WPA2-Personal | **2** | 0/0 | ✗ |
| 5 | ath8 | `P3A LAMPAYA` | 5 GHz | ✅ | ✓ | WPA/WPA2-Personal | **4** | 0/0 | ✗ |
| 6 | ath4 | `Simpangtiga` | 2.4G | ✅ | ✓ | WPA/WPA2-Personal | **1** | 0/0 | ✗ |
| 7 | ath15 | `Easymesh_Backhaul50710cbb` | 5 GHz | ✅ | ✗ tersembunyi | WPA/WPA2 | 32 | 0/0 | ✗ |
| 9 | ath5 | `RAJA KUALA` | 2.4G | ✅ | ✓ | **WPA2-Personal** (paling aman) | 32 | 0/0 | ✗ |
| 13 | ath11 | `212` | 5 GHz | ✅ | ✓ | WPA/WPA2-Personal | **2** | 0/0 | ✗ |

**Temuan penting Wi-Fi**

1. **Daya pancar 100 %** di semua SSID (tidak ada yang di-throttle).
2. **Batas klien per SSID sangat timpang**: `Simpangtiga` cuma **1** klien, `Alika Caffe` & `212` **2**, `DiGiCOM` **3**, `P3A LAMPAYA` **4**, sisanya 32. Ini "kuota klien" yang sengaja dikunci per SSID.
3. **Tidak ada rate-limit / bandwidth shaping per SSID** (`X_HW_UpRateLimit=0`, `X_HW_DownRateLimit=0`) → semua SSID rebutan bandwidth bebas.
4. **Tidak ada isolasi klien** (`X_HW_IsolationEnable=0`, `X_HW_PortIsolation=0`) → perangkat antar-SSID bisa saling melihat di `192.168.100.0/24`.
5. **Tidak ada VLAN per SSID** (`X_HW_VLAN` kosong) → semua SSID satu broadcast domain.
6. **WPS mati di semua SSID** (bagus untuk keamanan).
7. **802.11w / PMF mati** di semua SSID → frame manajemen tidak terproteksi.
8. **Kanal 2.4 GHz dikunci manual di kanal 6** (`AutoChannelEnable=0`) untuk semua SSID — tidak ada ACS di 2.4G.
9. **Kanal 5 GHz auto**, dengan daftar ACS kustom `149,153,157,161` (hanya 4 kanal yang diperbolehkan).
10. **Total gagal PSK tinggi**: `Alika Caffe` **492×**, `Simpangtiga` **401×**, `SAMSUNG` 161×, `212` 50×, `P3A LAMPAYA` 20× → indikasi banyak percobaan password salah (atau klien lama dengan password usang).
11. SSID `DiGiCOM.@Acut.net` saat ini **nonaktif** tetapi dikonfigurasi **tanpa password** — kalau dihidupkan, jadi jaringan terbuka.
12. Ada **2 SSID EasyMesh backhaul tersembunyi** (ID 3 & 7) — normal untuk mesh, tapi menambah beban radio.

---

## 4. WAN (3 koneksi)

| # | Nama | Mode | VLAN | NAT | Servis | Keterangan |
|---|---|---|---|---|---|---|
| 1 | `wan1.1.ip1` | IP_Routed, DHCP | **100** | OFF | `TR069_VOIP` | WAN manajemen/VoIP |
| 2 | `2_INTERNET_R_VID_241` | **PPPoE routed** | **241** | **ON** | `INTERNET` | Koneksi internet utama (user `20260000431`, MRU 1492, PAP, idle-disconnect 180 s) |
| 3 | `3_OTHER_B_VID_242` | **IP_Bridged** | **242** | OFF | `OTHER` | WAN bridge |

**Policy route aktif:**
- `SSID1, SSID5` → `wan1.1.ppp1` (internet PPPoE)
- `LAN1, LAN2, SSID2` → `wan1.2.ip1` (WAN bridge / VLAN 242)

> Artinya: **port LAN1–LAN2 dan SSID2 keluar lewat jalur yang berbeda** dari SSID utama. Perlu dicek apakah jalur ini memang memiliki akses internet.

**Tidak ada**: port mapping, port trigger, DMZ, static route, DDNS, VPN — semuanya 0 entri.

---

## 5. LAN, DHCP & IPv6

| Item | Nilai |
|---|---|
| IP LAN utama | `192.168.100.1/24` (aktif) |
| IP interface ke-2 | `192.168.2.1/24` (aktif, tapi pool DHCP-nya **nonaktif**) |
| DHCP server | **ON**, pool `192.168.100.2–254`, **lease 1020 detik (~17 menit)** |
| DNS yang dibagikan | `1.1.1.1`, `8.8.4.4` |
| Port LAN | 4 port aktif (`eth0:1`–`eth0:4`) |
| Port USB | Nonaktif (`NoLink`) |
| Maks. host LAN | 64 (daftar kontrol 32) |
| IPv6 WAN | **MATI** (`IPv6Capable=0`) |
| IPv6 LAN | RA + DHCPv6 ON, ND ON, alamat hanya `fe80::1` (link-local) |
| Deteksi konflik IP | ON |
| Deteksi loopback | ON |

---

## 6. Manajemen, akun & akses jarak jauh

| Item | Nilai |
|---|---|
| Akun web | `Admin` (UserLevel **1**) dan `Support` (UserLevel **0** = level tertinggi di skema Huawei) — keduanya aktif, password terenkripsi `PassMode=3` (salt + 10.000 iterasi) |
| Akun CLI | `root` (password terenkripsi, `EncryptMode=2`) |
| **Telnet** | **ON**, port 23; akses: LAN ✗ / WAN ✗ / **Wi-Fi ✓** |
| SSH | OFF (LAN & WAN) |
| HTTP/HTTPS | LAN ✓ (80/443), Wi-Fi ✓ (HTTP), WAN ✗ |
| Remote access | **OFF** (`X_HW_RemoteAccess.Enable=0`) |
| **TR-069 / CWMP** | **OFF** (`EnableCWMP=0`) — ACS URL `http://192.168.13.21:7547`, path `b287bed243531d824431b9fbad29df18`, user `gcn`; status ACS: tidak terhubung |
| App remote manage | OFF (URL & port kosong, `Ability=0`) |
| Syslog | Lokal ON level 7; server syslog eksternal OFF; `X_HW_LogCfg` → `192.168.100.1:6543` |
| Iperf speed test / KMC | tersedia (key KMC kosong, tidak aktif) |

---

## 7. Anomali & catatan keamanan

1. **Pola "Wi-Fi sewaan"** — 7 SSID aktif dengan nama tempat/usaha (`Alika Caffe`, `Simpangtiga`, `RAJA KUALA`, `P3A LAMPAYA`, `212`). Namun **tidak ada isolasi klien dan tidak ada VLAN**, jadi seluruh penyewa berada di satu jaringan datar `192.168.100.0/24` dan bisa saling mengakses. Ini risiko terbesar di konfigurasi ini.
2. **Telnet terbuka dari sisi Wi-Fi** (`TELNETWifiEnable=1`) — siapa pun yang nyambung ke SSID mana pun berpotensi mencapai port 23 CLI.
3. **DoS protection mati** (`X_HW_DosEnable=0`), hanya `IcmpRedirectEn=1` yang hidup.
4. **Parental control aktif** dengan daftar kata kunci: `sek, sex, porno, judi, domino, xnxx, nude, dewasa, ngentot, ngesek` — diterapkan ke **semua** perangkat (`MAC = FF:FF:FF:FF:FF:FF`), mode `Allow`, filter URL policy `0`.
5. **Auto reboot harian 05:16–05:17** + **jadwal mati Wi-Fi 05:00–05:01** → koneksi pasti putus setiap pagi sekitar 1–2 menit.
6. **Riwayat restart tinggi**: 187 reboot hardware + 40 reboot software; suhu Wi-Fi sempat **71 °C**, CPU **64 °C**.
7. **`SAMSUNG` (SSID1) menyimpan 161 kegagalan PSK** saat sudah nonaktif → pernah dipakai lalu password diganti/dihapus kliennya.
8. **Kredensial terenkripsi, bukan terhapus** — file XML ini berisi PPPoE, password web `Admin`/`Support`, PSK semua SSID, kredensial ACS, dan password CLI `root` dalam format `$2...` (AES-256 kunci perangkat). Siapa pun yang punya file ini + perangkat/alat dekripsi yang beredar bisa membukanya. **Jangan sebarkan file backup ini.**
9. Firmware kustom ISP (`INATELKOM`), versi Juli 2023 — cek apakah ada pembaruan keamanan yang dirilis ISP.

---

## 8. Cara verifikasi cepat di perangkat

```bash
# Web admin
http://192.168.100.1        (user: Support = level tertinggi, atau Admin)

# Telnet CLI (hanya bisa dari klien Wi-Fi, karena akses LAN dimatikan)
telnet 192.168.100.1 23
# contoh perintah yang berguna (jika shell tersedia):
#   display wifi ssid all / display wan all / display stat port all
```

Untuk audit ulang setelah mengubah konfigurasi, jalankan skrip parser di folder ini:

```bash
python3 audit/parse_ctree.py /tmp/arena-coding-uploads/hw_ctreeHG.xml
```

---

## 9. Lampiran — parameter `Enable` yang bernilai aktif

> **55 path unik** terdeteksi aktif (82 objek jika dihitung per-instance, karena mis. 7 SSID, 8 codec VoIP, 4 port LAN, 4 jadwal Wi-Fi). Daftar jalankan ulang dengan: `python3 audit/parse_ctree.py <file.xml> --enabled`.

| Path parameter | Nilai |
|---|---|
| `Service.VoiceService.1.VoiceProfile.1.Enable` | Enabled |
| `Service.VoiceService.1.VoiceProfile.1.RTP.RTCP.Enable` | 1 |
| `Service.VoiceService.1.VoiceProfile.1.Line.1.Codec.List.1.Enable` | 1 |
| `Service.StorageService.1.Enable` | 1 |
| `Service.X_CU_User.1.Enable` | 1 |
| `WANDevice.1.WANConnectionDevice.1.WANIPConnection.1.Enable` | 1 |
| `WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Enable` | 1 |
| `QueueManagement.Enable` | 1 |
| `QueueManagement.X_HW_QosEnable.enable` | 1 |
| `X_HW_Security.AclServices.X_HW_LocalAccess.Enable` | 1 |
| `X_HW_Security.AclServices.WanAccess.1.Enable` | 1 |
| `X_HW_Security.ParentalCtrl.Enable` | 1 |
| `X_HW_Security.ParentalCtrl.MAC.1.Enable` | 1 |
| `X_HW_Security.UsrSessionLimit.Enable` | 1 |
| `X_HW_Security.Firewall.Enable` | 1 |
| `X_HW_Security.X_HW_WANGlobalControl.Enable` | 1 |
| `X_HW_MainUPnP.Enable` | 1 |
| `X_HW_SlvUPnP.Enable` | 1 |
| `Time.Enable` | 1 |
| `UserInterface.X_HW_WebSslInfo.Enable` | 1 |
| `UserInterface.X_HW_WebUserInfo.{1,2}.Enable` | 1 |
| `DeviceInfo.X_HW_Syslog.Enable` | 1 (level 7) |
| `DeviceInfo.X_HW_ReConnect.Enable` | 1 |
| `DeviceInfo.TemperatureStatus.TemperatureSensor.{1,2,3}.Enable` | 1 |
| `LANDevice.1.WiFi.Radio.{1,2}.Enable` | 1 |
| `LANDevice.1.WLANConfiguration.{3,4,5,6,7,9,13}.Enable` | 1 |
| `LANDevice.1.LANHostConfigManagement.IPInterface.{1,2}.Enable` | 1 |
| `LANDevice.1.LANEthernetInterfaceConfig.{1,2,3,4}.Enable` | 1 |
| `LANDevice.1.X_HW_DHCPv6.Server.Enable` | 1 |
| `LANDevice.1.X_HW_RouterAdvertisement.Enable` | 1 |
| `LANDevice.1.X_HW_WLANShutDownCtrl.Enable` (+ Duration 1) | 1 |
| `X_HW_LED.Internet.Enable` | 1 |
| `X_HW_PonQualityMonitor.Enable` | 1 |
| `ContentSharing.Enable` | 1 |
| `X_HW_DataModel.Optical.Interface.1.Enable` | 1 |
| `X_HW_DataModel.SecurityCertAlarm.Enable` | 1 |
| `X_HW_IPv6.X_HW_NeighborDiscovery.InterfaceSetting.1.Enable` | 1 |
| `X_HW_AutoReboot.Enable` | 1 |
| `X_HW_WIFIInfo.X_HW_PskMassiveDetect.Enable` | 1 |
| `X_HW_CHL_SCAN.Enable` | 1 |
| `X_HW_SmartCAT.Enable` | 1 |
| `EasyMesh.Enable` | 1 |
| `X_HW_WifiCoverService.Enable` | 1 |
| `X_HW_SmartTopo.Enable` | 1 |
| `X_HW_OKC.Enable` | 1 |
| `SoftwareModules.ExecEnv.1.Enable` | 1 (`kernelapp` ACTIVE) |
| `X_HW_EAIInfo.Enable` + Game/Ping/Edu/Office/Video | 1 (status `on`) |
| `X_HW_BandWidthUpTo160.Enable` | 1 |
| `X_HW_LinkTurboInfo.Enable` | 1 |
