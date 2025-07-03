from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QLabel, QDialogButtonBox, QMessageBox
from vdm.logic.utils import format_size, get_disk_usage
import os
import subprocess

class EditDiskDialog(QDialog):
    def __init__(self, parent, discos):
        super().__init__(parent)
        self.setWindowTitle('Edit Disk Size')
        self.setModal(True)
        self.resize(400, 180)
        self.selected_disk = None
        # Detect RAM disks ativos via mount
        ram_disks = []
        try:
            mounts = subprocess.check_output(['mount'], text=True)
            for line in mounts.splitlines():
                if 'type tmpfs' in line:
                    import re
                    m = re.match(r'(.+) on (.+) type tmpfs .+size=([^, ]+)', line)
                    if m:
                        device, mountpoint, size = m.groups()
                    else:
                        parts = line.split()
                        device, mountpoint = parts[0], parts[2]
                        size = '-'
                    ram_disks.append({
                        'type': 'RAM Disk',
                        'device_or_file': device,
                        'mountpoint': mountpoint,
                        'size': size,
                        'status': 'Mounted'
                    })
        except Exception:
            pass
        # Remove system disks (mountpoints in MainWindow.SYSTEM_MOUNTPOINTS)
        system_mounts = set(getattr(parent, 'SYSTEM_MOUNTPOINTS', []))
        ram_disks = [d for d in ram_disks if d.get('mountpoint') and not any(d['mountpoint'].startswith(sysmp) for sysmp in system_mounts)]
        # Discos do json (file disks)
        file_disks = [d for d in discos if d.get('type') == 'File' and d.get('mountpoint') and not any(d['mountpoint'].startswith(sysmp) for sysmp in system_mounts)]
        self.discos = file_disks + ram_disks
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.disk_combo = QComboBox()
        self.disk_map = {}
        for idx, d in enumerate(self.discos):
            label = f"{d['type']} - {d['mountpoint']} ({d['device_or_file'] if 'device_or_file' in d else ''})"
            if d.get('type') == 'File':
                label += ' (unsupported)'
            self.disk_combo.addItem(label)
            self.disk_map[label] = d
            # Desabilita item se for File
            if d.get('type') == 'File':
                self.disk_combo.model().item(idx).setEnabled(False)
        self.disk_combo.setCurrentIndex(-1)  # Nenhum selecionado por padrão
        self.disk_combo.currentIndexChanged.connect(self.update_info)
        form.addRow('Disk:', self.disk_combo)
        self.info_label = QLabel()
        form.addRow('Current usage:', self.info_label)
        # Size suggestions
        self.size_combo = QComboBox()
        size_suggestions = ['128', '256', '512', '1024', '2048', '4096', '8192']
        self.size_combo.addItems(size_suggestions)
        self.size_combo.setEditable(True)
        self.size_edit = self.size_combo.lineEdit()
        self.size_edit.setPlaceholderText('Enter new size in MB (e.g. 1024)')
        self.size_edit.focusOutEvent = self.size_edit_focus_out
        form.addRow('New size (MB):', self.size_combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_info()

    def update_info(self):
        idx = self.disk_combo.currentIndex()
        if idx < 0 or (idx < len(self.discos) and self.discos[idx].get('type') == 'File'):
            self.info_label.setText('')
            self.size_edit.setText('')
            return
        disk = self.discos[idx]
        mountpoint = disk.get('mountpoint')
        try:
            used, total = get_disk_usage(mountpoint)
            used_mb = int(used / (1024*1024))
            total_mb = int(total / (1024*1024))
            self.info_label.setText(f"Used: {used_mb} MB / Total: {total_mb} MB")
            self.size_edit.setText(str(total_mb))
            self._used_mb = used_mb
        except Exception:
            self.info_label.setText('Unable to get usage info.')
            self.size_edit.setText('')
            self._used_mb = 0

    def size_edit_focus_out(self, event):
        try:
            val = int(float(self.size_edit.text().replace(',', '.')))
        except Exception:
            self.size_edit.setText(str(getattr(self, '_used_mb', 0)))
            return super(type(self.size_edit), self.size_edit).focusOutEvent(event)
        min_val = getattr(self, '_used_mb', 0)
        if val < min_val:
            self.size_edit.setText(str(min_val))
        return super(type(self.size_edit), self.size_edit).focusOutEvent(event)

    def accept(self):
        import subprocess
        idx = self.disk_combo.currentIndex()
        if idx < 0 or (idx < len(self.discos) and self.discos[idx].get('type') == 'File'):
            return
        disk = self.discos[idx]
        mountpoint = disk.get('mountpoint')
        new_size_mb = self.size_edit.text().strip().replace(',', '.')
        try:
            used, total = get_disk_usage(mountpoint)
        except Exception:
            used = 0
        used_mb = int(used / (1024*1024))
        try:
            new_mb = int(float(new_size_mb))
        except Exception:
            QMessageBox.warning(self, 'Invalid size', 'Please enter a valid number for the new size in MB (e.g. 1024).')
            return
        if new_mb < used_mb:
            self.size_edit.setText(str(used_mb))
            new_mb = used_mb
        # RAM Disk: size=...M
        new_size_str = f"{new_mb}M"
        # File Disk: converter para GB para o campo size
        new_size_gb = new_mb / 1024
        file_size_str = f"{new_size_gb:.2f}G"
        # --- Resize logic ---
        try:
            if disk['type'] == 'RAM Disk':
                subprocess.run(['sudo', 'mount', '-o', f'remount,size={new_size_str}', mountpoint], check=True)
                QMessageBox.information(self, 'Success', f'RAM Disk resized to {new_size_str}.')
            elif disk['type'] == 'File':
                device_file = disk['device_or_file']
                losetup = subprocess.check_output(['sudo', 'losetup', '-a'], text=True)
                loopdev = None
                for line in losetup.splitlines():
                    if device_file in line:
                        import re
                        m = re.match(r'(/dev/loop\d+):', line)
                        if m:
                            loopdev = m.group(1)
                            break
                if not loopdev:
                    QMessageBox.warning(self, 'Error', 'Loop device not found. Is the disk mounted?')
                    return
                subprocess.run(['sudo', 'umount', mountpoint], check=True)
                subprocess.run(['sudo', 'dd', 'if=/dev/zero', f'of={device_file}', 'bs=1M', f'count=0', f'seek={new_mb}'], check=True)
                subprocess.run(['sudo', 'e2fsck', '-f', loopdev], check=True)
                subprocess.run(['sudo', 'resize2fs', loopdev], check=True)
                subprocess.run(['sudo', 'mount', loopdev, mountpoint], check=True)
                subprocess.run(['sudo', 'chmod', '777', mountpoint], check=True)
                self.update_disk_size_in_json(device_file, mountpoint, file_size_str)
                QMessageBox.information(self, 'Success', f'File disk resized to {file_size_str}.')
            else:
                QMessageBox.warning(self, 'Error', 'Unsupported disk type.')
                return
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Resize failed', f'Error during resize:\n{e}')
            return
        super().accept()

    def update_disk_size_in_json(self, device_file, mountpoint, new_size_str):
        import json
        discos_json = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'discos.json')
        try:
            with open(discos_json, 'r') as f:
                discos = json.load(f)
            for d in discos:
                if d.get('device_or_file') == device_file and d.get('mountpoint') == mountpoint:
                    d['size'] = new_size_str
            with open(discos_json, 'w') as f:
                json.dump(discos, f, indent=2)
        except Exception:
            pass 
            pass 