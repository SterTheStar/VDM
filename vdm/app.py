import os
import datetime
import subprocess
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QInputDialog, QHeaderView, QComboBox, QCheckBox, QToolButton, QDialog)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
import qtawesome as qta
from vdm.logic.utils import resource_path
from vdm.logic.disks import load_disks, save_disks, add_disk, remove_disk, sync_disks_status, size_to_mb
from vdm.dialogs import RamDiskDialog, FileDiskDialog, show_full_license

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

    def init_ui(self):
        central_widget = CentralWidget(table=None)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Action buttons row (top)
        btn_layout = QHBoxLayout()
        self.btn_create_disk = QPushButton(qta.icon('fa5s.plus-circle'), 'Create Disk')
        self.btn_mount = QPushButton(qta.icon('fa5s.play'), 'Mount')
        self.btn_unmount = QPushButton(qta.icon('fa5s.eject'), 'Unmount')
        self.btn_delete = QPushButton(qta.icon('fa5s.trash'), 'Delete')
        self.btn_show_system = QToolButton()
        self.btn_show_system.setCheckable(True)
        self.btn_show_system.setChecked(False)
        self.btn_show_system.setIcon(qta.icon('fa5s.server'))
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
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        self.btn_about = QToolButton()
        self.btn_about.setIcon(qta.icon('fa5s.info-circle'))
        self.btn_about.setText('About')
        self.btn_about.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_about.clicked.connect(self.show_about)
        title_layout.addWidget(self.btn_about)
        layout.addLayout(title_layout)

        # Table
        self.table = QTableWidget(0, 5)
        central_widget.table = self.table
        self.table.setHorizontalHeaderLabels([
            'Type', 'Device/File', 'Mount Point', 'Size', 'Status'
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet('''
            QTableWidget { background: #f8fafd; alternate-background-color: #e6f0fa; font-size: 14px; }
            QHeaderView::section { background: #1976d2; color: white; font-weight: bold; font-size: 15px; height: 32px; }
            QTableWidget::item { padding: 8px; }
        ''')
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        self.table.setFont(QFont('Segoe UI', 12))
        self.table.setIconSize(QSize(24, 24))
        layout.addWidget(self.table)

        # Connect signals
        self.btn_create_disk.clicked.connect(self.create_disk)
        self.btn_mount.clicked.connect(self.mount_disk)
        self.btn_unmount.clicked.connect(self.unmount_disk)
        self.btn_delete.clicked.connect(self.delete_disk)
        self.table.cellDoubleClicked.connect(self.open_mount_dir)

    def update_table(self):
        self.discos = sync_disks_status(self.discos)
        save_disks(self.discos, self.discos_json)
        self.table.setRowCount(0)
        icon_ram = qta.icon('fa5s.memory')
        icon_file = qta.icon('fa5s.hdd')
        icon_mounted = qta.icon('fa5s.check-circle')
        icon_unmounted = qta.icon('fa5s.times-circle')
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        # 1. RAM disks (detected in system)
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
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    tipo_item = QTableWidgetItem(icon_ram, 'RAM Disk')
                    tipo_item.setTextAlignment(Qt.AlignCenter)
                    tipo_item.setFlags(flags)
                    self.table.setItem(row, 0, tipo_item)
                    item1 = QTableWidgetItem(device)
                    item1.setFlags(flags)
                    self.table.setItem(row, 1, item1)
                    item2 = QTableWidgetItem(mountpoint)
                    item2.setFlags(flags)
                    self.table.setItem(row, 2, item2)
                    item3 = QTableWidgetItem(size)
                    item3.setFlags(flags)
                    self.table.setItem(row, 3, item3)
                    status_item = QTableWidgetItem(icon_mounted, 'Mounted')
                    status_item.setTextAlignment(Qt.AlignCenter)
                    status_item.setFlags(flags)
                    self.table.setItem(row, 4, status_item)
        except Exception:
            pass
        # 2. File disks (persisted)
        for disk in self.discos:
            row = self.table.rowCount()
            self.table.insertRow(row)
            tipo_item = QTableWidgetItem(icon_file, disk['type'])
            tipo_item.setTextAlignment(Qt.AlignCenter)
            tipo_item.setFlags(flags)
            self.table.setItem(row, 0, tipo_item)
            item1 = QTableWidgetItem(disk['device_or_file'])
            item1.setFlags(flags)
            self.table.setItem(row, 1, item1)
            item2 = QTableWidgetItem(disk['mountpoint'])
            item2.setFlags(flags)
            self.table.setItem(row, 2, item2)
            item3 = QTableWidgetItem(disk['size'])
            item3.setFlags(flags)
            self.table.setItem(row, 3, item3)
            status_icon = icon_mounted if disk['status']=='Mounted' else icon_unmounted
            status_item = QTableWidgetItem(status_icon, disk['status'])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(flags)
            self.table.setItem(row, 4, status_item)
        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, 36)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def create_disk(self):
        tipo, ok = QInputDialog.getItem(self, 'Create Disk', 'Disk type:', ['RAM Disk', 'File Disk'], 0, False)
        if not ok:
            return
        if tipo == 'RAM Disk':
            self.create_ramdisk()
        else:
            self.create_file_disk()

    def create_ramdisk(self):
        dialog = RamDiskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            size, mountpoint = dialog.get_data()
            if not size or not mountpoint:
                QMessageBox.warning(self, 'Error', 'Fill in all fields.')
                return
            try:
                subprocess.run(['sudo', 'mkdir', '-p', mountpoint], check=True)
                cmd = ['sudo', 'mount', '-t', 'tmpfs', '-o', f'size={size}', 'tmpfs', mountpoint]
                subprocess.run(cmd, check=True)
                QMessageBox.information(self, 'Success', f'RAM Disk created and mounted at {mountpoint}.')
                self.update_table()
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, 'Error', f'Failed to create RAM Disk:\n{e}')

    def create_file_disk(self):
        dialog = FileDiskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            file_path, size, mountpoint = dialog.get_data()
            if not file_path or not size or not mountpoint:
                QMessageBox.warning(self, 'Error', 'Fill in all fields.')
                return
            try:
                subprocess.run(['sudo', 'dd', 'if=/dev/zero', f'of={file_path}', 'bs=1M', f'count={size_to_mb(size)}'], check=True)
                losetup_out = subprocess.check_output(['sudo', 'losetup', '--find', '--show', file_path], text=True).strip()
                loopdev = losetup_out
                subprocess.run(['sudo', 'mkfs.ext4', loopdev], check=True)
                subprocess.run(['sudo', 'mkdir', '-p', mountpoint], check=True)
                subprocess.run(['sudo', 'mount', loopdev, mountpoint], check=True)
                QMessageBox.information(self, 'Success', f'File disk created, formatted and mounted at {mountpoint}.')
                add_disk(self.discos, {
                    'type': 'File',
                    'device_or_file': file_path,
                    'mountpoint': mountpoint,
                    'size': size,
                    'status': 'Mounted'
                }, self.discos_json)
                self.update_table()
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, 'Error', f'Failed to create file disk:\n{e}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Unexpected error:\n{e}')

    def mount_disk(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'Warning', 'Select a disk in the table.')
            return
        tipo = self.table.item(row, 0).text()
        device_or_file = self.table.item(row, 1).text()
        mountpoint = self.table.item(row, 2).text()
        status = self.table.item(row, 4).text()
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
            self.update_table()
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Failed to mount disk:\n{e}')

    def unmount_disk(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'Warning', 'Select a disk in the table.')
            return
        tipo = self.table.item(row, 0).text()
        mountpoint = self.table.item(row, 2).text()
        status = self.table.item(row, 4).text()
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
            subprocess.run(['sudo', 'umount', mountpoint], check=True)
            QMessageBox.information(self, 'Success', f'Unmounted: {mountpoint}')
            self.update_table()
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Failed to unmount:\n{e}')

    def delete_disk(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, 'Warning', 'Select a disk in the table.')
            return
        tipo = self.table.item(row, 0).text()
        device_or_file = self.table.item(row, 1).text()
        mountpoint = self.table.item(row, 2).text()
        status = self.table.item(row, 4).text()
        if QMessageBox.question(self, 'Confirm', f'Are you sure you want to delete this disk?\n{device_or_file}') != QMessageBox.Yes:
            return
        try:
            if mountpoint != '-' and mountpoint and status == 'Mounted':
                try:
                    subprocess.run(['sudo', 'umount', mountpoint], check=True)
                except subprocess.CalledProcessError:
                    QMessageBox.critical(self, 'Error', f'Failed to unmount {mountpoint}.\nClose programs or terminals using the directory and try again.')
                    return
            if tipo == 'RAM Disk':
                try:
                    subprocess.run(['sudo', 'rmdir', mountpoint], check=True)
                except subprocess.CalledProcessError:
                    QMessageBox.warning(self, 'Warning', f'Could not remove directory {mountpoint}. Make sure it is empty and not mounted.')
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
                if loopdev:
                    subprocess.run(['sudo', 'losetup', '-d', loopdev], check=False)
                subprocess.run(['sudo', 'rm', '-f', device_or_file], check=False)
                try:
                    subprocess.run(['sudo', 'rmdir', mountpoint], check=True)
                except subprocess.CalledProcessError:
                    QMessageBox.warning(self, 'Warning', f'Could not remove directory {mountpoint}. Make sure it is empty and not mounted.')
                idx = next((i for i, d in enumerate(self.discos) if d['device_or_file'] == device_or_file and d['mountpoint'] == mountpoint), None)
                if idx is not None:
                    remove_disk(self.discos, idx, self.discos_json)
            QMessageBox.information(self, 'Success', 'Disk deleted.')
            self.update_table()
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Failed to delete disk:\n{e}')

    def open_mount_dir(self, row, col):
        mountpoint = self.table.item(row, 2).text()
        if mountpoint and os.path.exists(mountpoint):
            subprocess.Popen(['xdg-open', mountpoint])

    def show_about(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle('About VDM')
        layout = QVBoxLayout(about_dialog)
        label = QLabel(
            '<b>VDM</b> (Virtual Disk Manager)<br>'
            'Version 0.1 beta<br>'
            'Author: Esther (<a href="https://github.com/SterTheStar">github.com/SterTheStar</a>)<br>'
            '<br>'
            '<b>SourceCode:</b> <a href="">GPL v3.0</a><br>'
            '<b>License:</b> <a href="#gpl3">GPL v3.0</a><br>'
            'This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.'
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

    # ... (restante dos métodos da MainWindow, igual ao main.py, exceto o bloco if __name__ == '__main__') ... 