import os
import datetime
import subprocess
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QInputDialog, QHeaderView, QComboBox, QCheckBox, QToolButton, QDialog, QLineEdit, QAbstractItemView, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont
import qtawesome as qta
from vdm.logic.utils import resource_path, format_size, get_disk_usage, send_notification
from vdm.logic.disks import load_disks, save_disks, add_disk, remove_disk, sync_disks_status, size_to_mb
from vdm.dialogs import RamDiskDialog, FileDiskDialog, show_full_license
from vdm.createdisk import ModernCreateDiskDialog

# Custom widget para cada disco
class DiskListItem(QWidget):
    def __init__(self, icon, disk_type, device, mountpoint, size, status_icon, status_text, encrypted=False):
        super().__init__()
        self.setStyleSheet('background: transparent;')
        self.disk_encrypted = encrypted
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(16)
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(24, 24))
        layout.addWidget(icon_label)
        text = f"<b>{disk_type}</b>  |  {device}  |  {mountpoint}  |  {size}  "
        info_label = QLabel(text)
        info_label.setStyleSheet('background: transparent; color: #e0e0e0; font-size: 15px;')
        layout.addWidget(info_label)
        layout.addStretch()
        status_layout = QHBoxLayout()
        status_layout.setSpacing(4)
        if self.disk_encrypted:
            lock_label = QLabel()
            lock_label.setPixmap(qta.icon('fa5s.lock', color='white').pixmap(16, 16))
            status_layout.addWidget(lock_label)
        status_label = QLabel()
        status_label.setPixmap(status_icon.pixmap(18, 18))
        status_layout.addWidget(status_label)
        status_text_label = QLabel(status_text)
        status_text_label.setStyleSheet('background: transparent; color: #e0e0e0; font-size: 14px;')
        status_layout.addWidget(status_text_label)
        status_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addLayout(status_layout)

class DiskListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet('QListWidget { background: #111112; color: #e0e0e0; border: none; font-size: 14px; }')
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(False)
        self.setSpacing(2)

class CentralWidget(QWidget):
    def __init__(self, parent=None, table=None):
        super().__init__(parent)
        self.table = table

    def mousePressEvent(self, event):
        widget = self.childAt(event.pos())
        if not isinstance(widget, (QPushButton, QToolButton, QTableWidget)):
            if self.table:
                self.table.clearSelection()
        super().mousePressEvent(event)

class MainWindow(QMainWindow):
    SYSTEM_MOUNTPOINTS = [
        '/run', '/dev/shm', '/run/credentials/systemd-journald.service', '/tmp', '/run/user/1000', '/run/user', '/var/tmp', '/var/run', '/var/lock'
    ]
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Virtual Disk Manager')
        self.setGeometry(100, 100, 800, 500)
        self.discos_json = 'discos.json'
        self.discos = load_disks(self.discos_json)
        self.init_ui()
        self.update_table()
        # Monitoramento automático
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.monitor_disks)
        self.monitor_timer.start(15000)  # 15 segundos
        self.notified_full = set()

    def init_ui(self):
        central_widget = CentralWidget(table=None)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Action buttons row (top)
        btn_layout = QHBoxLayout()
        self.btn_create_disk = QPushButton(qta.icon('fa5s.plus-circle', color='white'), 'Create Disk')
        self.btn_mount = QPushButton(qta.icon('fa5s.play', color='white'), 'Mount')
        self.btn_unmount = QPushButton(qta.icon('fa5s.eject', color='white'), 'Unmount')
        self.btn_delete = QPushButton(qta.icon('fa5s.trash', color='white'), 'Delete')
        self.btn_show_system = QToolButton()
        self.btn_show_system.setCheckable(True)
        self.btn_show_system.setChecked(False)
        self.btn_show_system.setIcon(qta.icon('fa5s.server', color='white'))
        self.btn_show_system.setText('Show system disks')
        self.btn_show_system.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_show_system.clicked.connect(self.update_table)
        btn_layout.addWidget(self.btn_create_disk)
        btn_layout.addWidget(self.btn_mount)
        btn_layout.addWidget(self.btn_unmount)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_show_system)
        layout.addLayout(btn_layout)

        # Title row: label left, About button right (below action buttons)
        title_layout = QHBoxLayout()
        title_label = QLabel('Active Virtual Disks:')
        title_label.setStyleSheet('background: transparent;')
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        self.btn_edit = QToolButton()
        self.btn_edit.setIcon(qta.icon('fa5s.edit', color='white'))
        self.btn_edit.setText('Edit')
        self.btn_edit.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_edit.clicked.connect(self.open_edit_disk_dialog)
        self.btn_about = QToolButton()
        self.btn_about.setIcon(qta.icon('fa5s.info-circle', color='white'))
        self.btn_about.setText('About')
        self.btn_about.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_about.clicked.connect(self.show_about)
        title_layout.addWidget(self.btn_edit)
        title_layout.addWidget(self.btn_about)
        layout.addLayout(title_layout)

        # Lista customizada
        self.disk_list = DiskListWidget()
        central_widget.table = self.disk_list
        layout.addWidget(self.disk_list)

        # Connect signals
        self.btn_create_disk.clicked.connect(self.create_disk)
        self.btn_mount.clicked.connect(self.mount_disk)
        self.btn_unmount.clicked.connect(self.unmount_disk)
        self.btn_delete.clicked.connect(self.delete_disk)
        self.disk_list.itemDoubleClicked.connect(self.open_mount_dir)

    def update_table(self):
        from vdm.logic.utils import format_size, get_disk_usage
        self.discos = sync_disks_status(self.discos)
        save_disks(self.discos, self.discos_json)
        self.disk_list.clear()
        icon_ram = qta.icon('fa5s.memory', color='white')
        icon_file = qta.icon('fa5s.hdd', color='white')
        icon_mounted = qta.icon('fa5s.check-circle', color='white')
        icon_unmounted = qta.icon('fa5s.times-circle', color='white')
        # RAM disks
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
                    if not self.btn_show_system.isChecked() and any(mountpoint == sysmp or mountpoint.startswith(sysmp + '/') for sysmp in self.SYSTEM_MOUNTPOINTS):
                        continue
                    try:
                        used, total = get_disk_usage(mountpoint)
                        size_str = f"{format_size(used)} / {format_size(total)}"
                    except Exception:
                        size_str = format_size(size)
                    disk_dict = {
                        'type': 'RAM Disk',
                        'device_or_file': device,
                        'mountpoint': mountpoint,
                        'size': size,
                        'status': 'Mounted'
                    }
                    item_widget = DiskListItem(icon_ram, 'RAM Disk', device, mountpoint, size_str, icon_mounted, 'Mounted', False)
                    item = QListWidgetItem()
                    item.setSizeHint(item_widget.sizeHint())
                    item.setData(Qt.UserRole, disk_dict)
                    self.disk_list.addItem(item)
                    self.disk_list.setItemWidget(item, item_widget)
        except Exception:
            pass
        # File disks
        for disk in self.discos:
            if disk['status'] == 'Mounted' and os.path.exists(disk['mountpoint']):
                try:
                    used, total = get_disk_usage(disk['mountpoint'])
                    size_str = f"{format_size(used)} / {format_size(total)}"
                except Exception:
                    size_str = format_size(disk['size'])
            else:
                size_str = format_size(disk['size'])
            icon = icon_file
            status_icon = icon_mounted if disk['status']=='Mounted' else icon_unmounted
            item_widget = DiskListItem(icon, disk['type'], disk['device_or_file'], disk['mountpoint'], size_str, status_icon, disk['status'], disk.get('encrypted', False))
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.UserRole, disk)
            self.disk_list.addItem(item)
            self.disk_list.setItemWidget(item, item_widget)

    def create_disk(self):
        dialog = ModernCreateDiskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data['type'] == 'RAM Disk':
                size = data['size']
                mountpoint = data['mountpoint']
                if not size or not mountpoint:
                    QMessageBox.warning(self, 'Error', 'Fill in all fields.')
                    return
                try:
                    subprocess.run(['sudo', 'mkdir', '-p', mountpoint], check=True)
                    cmd = ['sudo', 'mount', '-t', 'tmpfs', '-o', f'size={size}', 'tmpfs', mountpoint]
                    subprocess.run(cmd, check=True)
                    QMessageBox.information(self, 'Success', f'RAM Disk created and mounted at {mountpoint}.')
                    send_notification('RAM Disk Created', f'RAM Disk mounted at {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.png')))
                    self.update_table()
                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(self, 'Error', f'Failed to create RAM Disk:\n{e}')
                    send_notification('Error', f'Failed to create RAM Disk at {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
            else:
                file_path = data['file']
                size = data['size']
                mountpoint = data['mountpoint']
                encrypt = data['encrypt']
                password = data['password']
                if not file_path or not size or not mountpoint:
                    QMessageBox.warning(self, 'Error', 'Fill in all fields.')
                    return
                if encrypt and (not password or len(password) < 3):
                    QMessageBox.warning(self, 'Error', 'Password required for encryption (min 3 chars).')
                    return
                try:
                    subprocess.run(['sudo', 'dd', 'if=/dev/zero', f'of={file_path}', 'bs=1M', f'count={size_to_mb(size)}'], check=True)
                    if encrypt:
                        # LUKS format
                        luks_cmd = ['sudo', 'cryptsetup', 'luksFormat', file_path, '--batch-mode']
                        p = subprocess.Popen(luks_cmd, stdin=subprocess.PIPE, text=True)
                        p.communicate(password + '\n')
                        if p.returncode != 0:
                            raise Exception('cryptsetup luksFormat failed')
                        # Open LUKS
                        luks_name = os.path.basename(file_path) + '_luks'
                        open_cmd = ['sudo', 'cryptsetup', 'luksOpen', file_path, luks_name]
                        p = subprocess.Popen(open_cmd, stdin=subprocess.PIPE, text=True)
                        p.communicate(password + '\n')
                        if p.returncode != 0:
                            raise Exception('cryptsetup luksOpen failed')
                        loopdev = f'/dev/mapper/{luks_name}'
                    else:
                        losetup_out = subprocess.check_output(['sudo', 'losetup', '--find', '--show', file_path], text=True).strip()
                        loopdev = losetup_out
                    subprocess.run(['sudo', 'mkfs.ext4', loopdev], check=True)
                    subprocess.run(['sudo', 'mkdir', '-p', mountpoint], check=True)
                    subprocess.run(['sudo', 'mount', loopdev, mountpoint], check=True)
                    subprocess.run(['sudo', 'chmod', '777', mountpoint], check=True)
                    QMessageBox.information(self, 'Success', f'File disk created, formatted and mounted at {mountpoint}.')
                    add_disk(self.discos, {
                        'type': 'File',
                        'device_or_file': file_path,
                        'mountpoint': mountpoint,
                        'size': size,
                        'status': 'Mounted',
                        'encrypted': bool(encrypt)
                    }, self.discos_json)
                    send_notification('File Disk Created', f'File disk mounted at {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.png')))
                    self.update_table()
                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(self, 'Error', f'Failed to create file disk:\n{e}')
                    send_notification('Error', f'Failed to create file disk at {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Unexpected error:\n{e}')
                    send_notification('Error', f'Failed to create file disk at {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))

    def mount_disk(self):
        row = self.disk_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'Warning', 'Select a disk in the table.')
            return
        item = self.disk_list.item(row)
        disk = item.data(Qt.UserRole)
        tipo = disk.get('type')
        device_or_file = disk.get('device_or_file')
        mountpoint = disk.get('mountpoint')
        status = disk.get('status')
        if tipo != 'File':
            QMessageBox.warning(self, 'Warning', 'Only file disks can be mounted here.')
            return
        if status == 'Mounted':
            QMessageBox.information(self, 'Info', 'This disk is already mounted.')
            return
        if mountpoint == '-' or not mountpoint:
            mountpoint, ok = QInputDialog.getText(self, 'Mount Point', 'Enter mount point:')
            if not ok or not mountpoint.strip():
                QMessageBox.warning(self, 'Warning', 'Mount point not provided.')
                return
            mountpoint = mountpoint.strip()
        try:
            if disk and disk.get('encrypted'):
                # Solicitar senha
                luks_name = os.path.basename(device_or_file) + '_luks'
                luks_path = f'/dev/mapper/{luks_name}'
                if not os.path.exists(luks_path):
                    password, ok = QInputDialog.getText(self, 'Password Required', f'Enter password to unlock encrypted disk:\n{device_or_file}', QLineEdit.Password)
                    if not ok or not password:
                        QMessageBox.warning(self, 'Warning', 'Password not provided.')
                        return
                    open_cmd = ['sudo', 'cryptsetup', 'luksOpen', device_or_file, luks_name]
                    p = subprocess.Popen(open_cmd, stdin=subprocess.PIPE, text=True)
                    p.communicate(password + '\n')
                    if p.returncode != 0:
                        QMessageBox.critical(self, 'Error', 'Failed to unlock encrypted disk.')
                        send_notification('Error', f'Failed to unlock encrypted disk {device_or_file}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
                        return
                loopdev = luks_path
            else:
                loopdev = None
                losetup = subprocess.check_output(['sudo', 'losetup', '-a'], text=True)
                for line in losetup.splitlines():
                    if device_or_file in line:
                        import re
                        m = re.match(r'(/dev/loop\d+):', line)
                        if m:
                            loopdev = m.group(1)
                            break
                if not loopdev:
                    loopdev = subprocess.check_output(['sudo', 'losetup', '--find', '--show', device_or_file], text=True).strip()
            subprocess.run(['sudo', 'mkdir', '-p', mountpoint], check=True)
            subprocess.run(['sudo', 'mount', loopdev, mountpoint], check=True)
            QMessageBox.information(self, 'Success', f'Disk mounted at {mountpoint}.')
            send_notification('Disk Mounted', f'Disk mounted at {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.png')))
            self.update_table()
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Failed to mount disk:\n{e}')
            send_notification('Error', f'Failed to mount disk at {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))

    def unmount_disk(self):
        row = self.disk_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'Warning', 'Select a disk in the table.')
            return
        item = self.disk_list.item(row)
        disk = item.data(Qt.UserRole)
        tipo = disk.get('type')
        mountpoint = disk.get('mountpoint')
        status = disk.get('status')
        device_or_file = disk.get('device_or_file')
        if tipo == 'RAM Disk':
            QMessageBox.information(self, 'Info', 'RAM disks cannot be unmounted. Use Delete to remove them.')
            return
        if mountpoint == '-' or not mountpoint:
            QMessageBox.warning(self, 'Warning', 'This disk is not mounted.')
            return
        if status != 'Mounted':
            QMessageBox.information(self, 'Info', 'This disk is already unmounted.')
            return
        try:
            subprocess.run(['sudo', 'umount', mountpoint], check=True, capture_output=True, text=True)
            if disk and disk.get('encrypted'):
                luks_name = os.path.basename(device_or_file) + '_luks'
                subprocess.run(['sudo', 'cryptsetup', 'luksClose', luks_name], check=True)
                # Desassociar loop device
                try:
                    losetup = subprocess.check_output(['sudo', 'losetup', '-a'], text=True)
                    for line in losetup.splitlines():
                        if device_or_file in line:
                            import re
                            m = re.match(r'(/dev/loop\d+):', line)
                            if m:
                                loopdev = m.group(1)
                                subprocess.run(['sudo', 'losetup', '-d', loopdev], check=False)
                                break
                except Exception:
                    pass
            QMessageBox.information(self, 'Success', f'Unmounted: {mountpoint}')
            send_notification('Disk Unmounted', f'Disk unmounted from {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.png')))
            self.update_table()
        except subprocess.CalledProcessError as e:
            err = e.stderr or str(e)
            if 'alvo ocupado' in err or 'target is busy' in err:
                QMessageBox.critical(self, 'Error', f'Could not unmount {mountpoint}: target is busy. Close all programs or terminals using this directory and try again.')
                send_notification('Error', f'Could not unmount {mountpoint}: target is busy.', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
            else:
                QMessageBox.critical(self, 'Error', f'Failed to unmount:\n{err}')
                send_notification('Error', f'Failed to unmount {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))

    def delete_disk(self):
        row = self.disk_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'Warning', 'Select a disk in the table.')
            return
        item = self.disk_list.item(row)
        disk = item.data(Qt.UserRole)
        tipo = disk.get('type')
        device_or_file = disk.get('device_or_file')
        mountpoint = disk.get('mountpoint')
        status = disk.get('status')
        if QMessageBox.question(self, 'Confirm', f'Are you sure you want to delete this disk?\n{device_or_file}') != QMessageBox.Yes:
            return
        try:
            if mountpoint != '-' and mountpoint and status == 'Mounted':
                try:
                    subprocess.run(['sudo', 'umount', mountpoint], check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e:
                    err = e.stderr or str(e)
                    if 'alvo ocupado' in err or 'target is busy' in err:
                        QMessageBox.critical(self, 'Error', f'Could not unmount {mountpoint}: target is busy. Close all programs or terminals using this directory and try again.')
                        send_notification('Error', f'Could not unmount {mountpoint}: target is busy.', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
                    else:
                        QMessageBox.critical(self, 'Error', f'Failed to unmount {mountpoint}.\n{err}')
                        send_notification('Error', f'Failed to unmount {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
                    return
            if tipo == 'RAM Disk':
                try:
                    subprocess.run(['sudo', 'rmdir', mountpoint], check=True)
                except subprocess.CalledProcessError:
                    QMessageBox.warning(self, 'Warning', f'Could not remove directory {mountpoint}. Make sure it is empty and not mounted.')
                    send_notification('Error', f'Could not remove directory {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
            elif tipo == 'File':
                loopdev = None
                try:
                    losetup = subprocess.check_output(['sudo', 'losetup', '-a'], text=True)
                    for line in losetup.splitlines():
                        if device_or_file in line:
                            import re
                            m = re.match(r'(/dev/loop\d+):', line)
                            if m:
                                loopdev = m.group(1)
                                break
                except Exception:
                    pass
                # Se for criptografado, fechar LUKS e desassociar loop
                if disk and disk.get('encrypted'):
                    luks_name = os.path.basename(device_or_file) + '_luks'
                    try:
                        subprocess.run(['sudo', 'cryptsetup', 'luksClose', luks_name], check=False)
                    except Exception:
                        pass
                    try:
                        if loopdev:
                            subprocess.run(['sudo', 'losetup', '-d', loopdev], check=False)
                    except Exception:
                        pass
                if loopdev:
                    subprocess.run(['sudo', 'losetup', '-d', loopdev], check=False)
                subprocess.run(['sudo', 'rm', '-f', device_or_file], check=False)
                try:
                    subprocess.run(['sudo', 'rmdir', mountpoint], check=True)
                except subprocess.CalledProcessError:
                    QMessageBox.warning(self, 'Warning', f'Could not remove directory {mountpoint}. Make sure it is empty and not mounted.')
                    send_notification('Error', f'Could not remove directory {mountpoint}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
                idx = next((i for i, d in enumerate(self.discos) if d['device_or_file'] == device_or_file and d['mountpoint'] == mountpoint), None)
                if idx is not None:
                    remove_disk(self.discos, idx, self.discos_json)
            QMessageBox.information(self, 'Success', 'Disk deleted.')
            send_notification('Disk Deleted', f'Disk {device_or_file} deleted.', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.png')))
            self.update_table()
        except subprocess.CalledProcessError as e:
            err = e.stderr or str(e)
            QMessageBox.critical(self, 'Error', f'Failed to delete disk:\n{err}')
            send_notification('Error', f'Failed to delete disk {device_or_file}', icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))

    def open_mount_dir(self, item):
        # item é o QListWidgetItem
        disk = item.data(Qt.UserRole)
        mountpoint = disk.get('mountpoint')
        if mountpoint and os.path.exists(mountpoint):
            subprocess.Popen(['xdg-open', mountpoint])

    def show_about(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle('About VDM')
        layout = QVBoxLayout(about_dialog)
        label = QLabel(
            '<b>VDM</b> (Virtual Disk Manager)<br>'
            'Version 0.1.2 beta<br>'
            'Author: Esther (<a href="https://github.com/SterTheStar">github.com/SterTheStar</a>)<br>'
            '<br>'
            '<b>Source code:</b> <a href="https://github.com/SterTheStar/VDM">github.com/SterTheStar/VDM</a><br>'
            '<b>License:</b> <a href="#gpl3">GPL v3.0</a> &mdash; <span style="font-size:11px; color:#aaa;">Free software under GPL v3.0.</span>'
        )
        label.setOpenExternalLinks(False)
        label.linkActivated.connect(self._about_link_clicked)
        layout.addWidget(label)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(about_dialog.accept)
        layout.addWidget(close_btn)
        about_dialog.exec_()

    def _about_link_clicked(self, link):
        if link == '#gpl3':
            show_full_license(self)

    def open_edit_disk_dialog(self):
        from vdm.editdisk import EditDiskDialog
        dlg = EditDiskDialog(self, self.discos)
        dlg.exec_()

    def monitor_disks(self):
        from vdm.logic.utils import get_disk_usage, send_notification, format_size
        for disk in self.discos:
            if disk.get('status') == 'Mounted' and os.path.exists(disk.get('mountpoint', '')):
                try:
                    used, total = get_disk_usage(disk['mountpoint'])
                    if total > 0:
                        percent = used / total
                        if percent >= 0.9:
                            key = (disk.get('device_or_file'), disk.get('mountpoint'))
                            if key not in self.notified_full:
                                send_notification('Disk Almost Full', f"{disk['mountpoint']}: {format_size(used)} / {format_size(total)} ({percent*100:.0f}%) used.", icon=os.path.abspath(os.path.join(os.path.dirname(__file__), '../vdm-bin/icon.ico')))
                                self.notified_full.add(key)
                        else:
                            key = (disk.get('device_or_file'), disk.get('mountpoint'))
                            if key in self.notified_full:
                                self.notified_full.remove(key)
                except Exception:
                    pass
        self.update_table()