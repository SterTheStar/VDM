# VDM - Virtual Disk Manager

**VDM (Virtual Disk Manager)** is a modern, user-friendly tool to create, mount, unmount, and manage RAM disks and file-based virtual disks on Linux.

---

## Features
- Create RAM disks (tmpfs) and file-based virtual disks (loop devices)
- Mount, unmount, and delete disks with a click
- Persistent file disks, volatile RAM disks
- Beautiful, intuitive interface (PyQt5)
- Quick presets for disk size and mount points
- See all active and historical disks in a single view
- Open mount points in your file manager
- System disk filtering
- About dialog with license and author info

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SterTheStar/vdm.git
   cd vdm
   ```
2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the app:**
   ```bash
   python main.py
   ```

---

## Requirements
- Linux (with sudo privileges)
- Python 3.7+
- PyQt5

---

## License

This project is licensed under the **GPL v3.0**. See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.html) for details.

---

## Author

**Esther** [github.com/SterTheStar](https://github.com/SterTheStar)

---

## Notes
- RAM disks are volatile: data is lost after unmount or reboot.
- File disks are persistent as long as the backing file exists.
- Some actions require `sudo` (mount, unmount, losetup, etc).

---

Enjoy using **VDM**! 
