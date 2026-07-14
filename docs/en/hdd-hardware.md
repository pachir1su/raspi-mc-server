# HDD form factor, enclosure, and power

This server stores worlds and backups under `/mnt/minecraft` on a USB HDD. A
momentary disconnect can become a failed world write or filesystem corruption,
not merely lag, so verify the physical format and power path before capacity.

## Interpreting the `100 × 700 mm` measurement

If this meant approximately **100 × 70 mm**, it matches a typical **2.5-inch
SATA HDD**. One real 2.5-inch family is 69.85mm wide and 100.35mm deep. A
700mm dimension is 70cm and is not a laptop HDD. Measure all three axes again.

| Measurement | Common 2.5-inch value | Meaning |
|---|---:|---|
| Depth | about 100mm | matches the reported `100` |
| Width | about 70mm | `700` is likely a `70.0` typo |
| Height | 7mm or 9.5mm | determines enclosure fit |

“7 versus 10” normally means **7mm versus 9.5mm (about 10mm) height**, not a
7-inch or 10-inch disk. The exact model's manufacturer sheet is authoritative.
The [Seagate 2.5-inch data sheet](https://www.seagate.com/www-content/product-content/barracuda-fam/barracuda-new/files/barracuda-2-5-ds1907-1-1609us.pdf)
shows a 69.85 × 100.35mm footprint, 7mm models, and model-specific startup
current.

## 2.5-inch 7mm versus 9.5mm

| Item | 7mm | 9.5mm (often called “10mm”) |
|---|---|---|
| Typical origin | thin laptop HDD/SSD | older/general laptop HDD |
| In a 9.5mm enclosure | fits but may move | fits |
| In a 7mm-only enclosure | fits | lid will not close |
| Fix | use the supplied spacer/pad | buy a 9.5mm-compatible enclosure |

Look for **“2.5-inch SATA, 7/9.5mm, USB 3.x, UASP”**. M.2 SATA, M.2 NVMe,
3.5-inch, and IDE enclosures are different. Confirm the drive has the joined
wide 15-pin power and narrow 7-pin data sections of a **22-pin SATA** connector.

Enclosure checklist:

1. Correct 2.5-inch SATA interface and height.
2. USB 3.0 or newer with UASP.
3. A bridge that passes SMART data on Raspberry Pi.
4. Short, sturdy cable and secure connectors.
5. Metal or ventilated construction for continuous use.
6. A powered USB hub or enclosure DC input when bus power is marginal.

## Distinguishing a 3.5-inch HDD

A 3.5-inch disk is roughly **147 × 101.6 × 20–26.1mm**. It needs **12V as
well as 5V**, so Raspberry Pi USB cannot power it. Use a 3.5-inch USB enclosure
or dock with its own adapter. The [Seagate 3.5-inch data sheet](https://www.seagate.com/www-content/product-content/pipeline-fam/pipeline-hd/video-3-5-hdd/en-us/docs/video-3-5-hdd-data-sheet-ds1783-2-1306us.pdf)
lists up to 101.6 × 146.99 × 26.11mm, 5V/12V input, and 2A typical 12V startup
current for these example models.

| Device | Required connection |
|---|---|
| 2.5-inch SATA HDD | SATA-to-USB 3 enclosure; bus power only after testing, otherwise powered hub |
| 3.5-inch SATA HDD | enclosure/dock with its **own 12V adapter** |
| Finished external HDD | original cable and original power adapter |
| M.2 SSD | M.2 enclosure matching SATA or NVMe, not a laptop-HDD enclosure |

## What happens without external power

Raspberry Pi 4B's recommended input is **5V 3A**, while all USB peripherals
share a limited downstream power budget. Follow the official [Raspberry Pi
hardware documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
and [power guidance](https://www.raspberrypi.com/documentation/computers/getting-started.html):
use a sound 15W-class supply and a short, good USB-C cable.

A 2.5-inch HDD can look economical after spin-up but draw much more while its
platters start. The example data sheet lists 1.0–1.2A startup current at 5V.
The Pi, fan, and other USB devices share the same budget, so one successful
boot does not prove unattended stability.

Insufficient power can cause:

- repeated spin-up or clicking;
- `/dev/sda` disappearance, USB resets, or UAS errors;
- `/mnt/minecraft` I/O errors, Paper stalls, or failed chunk saves;
- undervoltage/throttling, low TPS, and pauses;
- failed boots, reboots, ext4 damage, or world corruption.

For an unattended server, prefer a **self-powered USB 3 hub or powered
enclosure**. Connect the hub's data uplink to the Pi and use the adapter
specified by its manufacturer. The official [Raspberry Pi USB Hub
documentation](https://www.raspberrypi.com/documentation/accessories/usb.html)
describes up to 5V 3A downstream when that hub is self-powered.

Avoid unverified Y-cables, hubs with unclear back-power protection, attempting
to bus-power a 3.5-inch disk, and unplugging an active drive.

## Headless checks after connection

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,FSTYPE,MOUNTPOINTS
lsusb -t
findmnt /mnt/minecraft
vcgencmd get_throttled
sudo dmesg -T | grep -Ei 'under-voltage|voltage|usb|uas|reset|I/O error'
```

`get_throttled=0x0` is the healthy result. Check again while Paper and a backup
are active. Repeated SuperSpeed resets, UAS/I/O errors, or undervoltage mean
fixing power and cabling before repairing the filesystem.

SMART support depends on the USB bridge:

```bash
sudo apt install -y smartmontools
sudo smartctl --scan-open
sudo smartctl -a /dev/sda
# If the bridge requests SAT mode
sudo smartctl -a -d sat /dev/sda
```

## Installation checklist

- [ ] Confirm approximately `100 × 70 × 7/9.5mm`.
- [ ] Use a USB 3 enclosure for the correct 2.5-inch SATA height.
- [ ] Use a dedicated 12V adapter for every 3.5-inch disk.
- [ ] Power the Pi from a stable 5V 3A supply.
- [ ] Connect the HDD to a blue USB 3 port.
- [ ] Relieve cable strain, isolate vibration, and provide airflow.
- [ ] Confirm `get_throttled=0x0` and no USB reset/I/O errors.
- [ ] Never force Paper/bot startup when `/mnt/minecraft` is absent.
- [ ] Keep an important backup on another PC or disk.

Continue with [headless HDD setup](headless-setup.md#7-prepare-the-500gb-hdd)
and [the missing-HDD runbook](operator-runbook.md#when-the-hdd-disappears).
