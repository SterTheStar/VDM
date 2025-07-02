import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QInputDialog, QHeaderView, QComboBox, QCheckBox, QToolButton, QTextEdit, QToolBar, QAction
)
import subprocess
import re
from PyQt5.QtGui import QIcon, QBrush, QColor, QFont
from PyQt5.QtCore import Qt, QSize
import json
import os
import datetime
import qtawesome as qta

def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

class CentralWidget(QWidget):
    def __init__(self, parent=None, table=None):
        super().__init__(parent)
        self.table = table

    def mousePressEvent(self, event):
        widget = self.childAt(event.pos())
        # Se não for botão nem tabela, desmarca seleção
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
        self.discos = self.load_disks()
        self.init_ui()
        self.update_table()

    def log(self, message):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{now}] {message}')

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

        # Tabela de discos virtuais customizada
        self.table = QTableWidget(0, 5)
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

        # Conectar sinais
        self.btn_create_disk.clicked.connect(self.create_disk)
        self.btn_mount.clicked.connect(self.mount_disk)
        self.btn_unmount.clicked.connect(self.unmount_disk)
        self.btn_delete.clicked.connect(self.delete_disk)
        self.table.cellDoubleClicked.connect(self.open_mount_dir)

    def load_disks(self):
        if os.path.exists(self.discos_json):
            with open(self.discos_json, 'r') as f:
                return json.load(f)
        return []

    def save_disks(self):
        with open(self.discos_json, 'w') as f:
            json.dump(self.discos, f, indent=2)

    def add_disk(self, disk):
        if disk['type'] == 'File':
            self.discos.append(disk)
            self.save_disks()

    def remove_disk(self, idx):
        self.discos.pop(idx)
        self.save_disks()

    def update_table(self):
        self.sync_disks_status()
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

    def sync_disks_status(self):
        try:
            mounts = subprocess.check_output(['mount'], text=True)
        except Exception:
            mounts = ''
        try:
            losetup = subprocess.check_output(['sudo', 'losetup', '-a'], text=True)
        except Exception:
            losetup = ''
        for disk in self.discos:
            if disk['type'] == 'File':
                loopdev = None
                for line in losetup.splitlines():
                    if disk['device_or_file'] in line:
                        m = re.match(r'(/dev/loop\d+):', line)
                        if m:
                            loopdev = m.group(1)
                            break
                if loopdev and any(loopdev in mline for mline in mounts.splitlines()):
                    disk['status'] = 'Mounted'
                else:
                    disk['status'] = 'Unmounted'
        self.save_disks()

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
                self.log(f'Created and mounted RAM Disk at {mountpoint} ({size})')
                self.update_table()
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, 'Error', f'Failed to create RAM Disk:\n{e}')
                self.log(f'Failed to create RAM Disk at {mountpoint}: {e}')

    def create_file_disk(self):
        dialog = FileDiskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            file_path, size, mountpoint = dialog.get_data()
            if not file_path or not size or not mountpoint:
                QMessageBox.warning(self, 'Error', 'Fill in all fields.')
                return
            try:
                subprocess.run(['sudo', 'dd', 'if=/dev/zero', f'of={file_path}', 'bs=1M', f'count={self._size_to_mb(size)}'], check=True)
                losetup_out = subprocess.check_output(['sudo', 'losetup', '--find', '--show', file_path], text=True).strip()
                loopdev = losetup_out
                subprocess.run(['sudo', 'mkfs.ext4', loopdev], check=True)
                subprocess.run(['sudo', 'mkdir', '-p', mountpoint], check=True)
                subprocess.run(['sudo', 'mount', loopdev, mountpoint], check=True)
                QMessageBox.information(self, 'Success', f'File disk created, formatted and mounted at {mountpoint}.')
                self.log(f'Created, formatted and mounted file disk {file_path} at {mountpoint} ({size})')
                self.add_disk({
                    'type': 'File',
                    'device_or_file': file_path,
                    'mountpoint': mountpoint,
                    'size': size,
                    'status': 'Mounted'
                })
                self.update_table()
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, 'Error', f'Failed to create file disk:\n{e}')
                self.log(f'Failed to create file disk {file_path}: {e}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Unexpected error:\n{e}')
                self.log(f'Unexpected error creating file disk {file_path}: {e}')

    def _size_to_mb(self, size_str):
        size_str = size_str.strip().upper()
        if size_str.endswith('G'):
            return int(float(size_str[:-1]) * 1024)
        elif size_str.endswith('M'):
            return int(float(size_str[:-1]))
        else:
            raise ValueError('Size must end with M or G')

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
                    m = re.match(r'(/dev/loop\d+):', line)
                    if m:
                        loopdev = m.group(1)
                        break
            if not loopdev:
                loopdev = subprocess.check_output(['sudo', 'losetup', '--find', '--show', device_or_file], text=True).strip()
            subprocess.run(['sudo', 'mkdir', '-p', mountpoint], check=True)
            subprocess.run(['sudo', 'mount', loopdev, mountpoint], check=True)
            QMessageBox.information(self, 'Success', f'Disk mounted at {mountpoint}.')
            self.log(f'Mounted file disk {device_or_file} at {mountpoint}')
            self.update_table()
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Failed to mount disk:\n{e}')
            self.log(f'Failed to mount file disk {device_or_file}: {e}')

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
            self.log(f'Unmounted disk at {mountpoint}')
            self.update_table()
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Failed to unmount:\n{e}')
            self.log(f'Failed to unmount {mountpoint}: {e}')

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
                    self.log(f'Unmounted disk at {mountpoint} before deletion')
                except subprocess.CalledProcessError:
                    QMessageBox.critical(self, 'Error', f'Failed to unmount {mountpoint}.\nClose programs or terminals using the directory and try again.')
                    self.log(f'Failed to unmount {mountpoint} before deletion')
                    return
            if tipo == 'RAM Disk':
                try:
                    subprocess.run(['sudo', 'rmdir', mountpoint], check=True)
                    self.log(f'Removed RAM disk mount point {mountpoint}')
                except subprocess.CalledProcessError:
                    QMessageBox.warning(self, 'Warning', f'Could not remove directory {mountpoint}. Make sure it is empty and not mounted.')
                    self.log(f'Failed to remove RAM disk mount point {mountpoint}')
            elif tipo == 'File':
                loopdev = None
                try:
                    losetup = subprocess.check_output(['sudo', 'losetup', '-a'], text=True)
                    for line in losetup.splitlines():
                        if device_or_file in line:
                            m = re.match(r'(/dev/loop\d+):', line)
                            if m:
                                loopdev = m.group(1)
                                break
                except Exception:
                    pass
                if loopdev:
                    subprocess.run(['sudo', 'losetup', '-d', loopdev], check=False)
                    self.log(f'Detached loop device {loopdev}')
                subprocess.run(['sudo', 'rm', '-f', device_or_file], check=False)
                self.log(f'Removed file {device_or_file}')
                try:
                    subprocess.run(['sudo', 'rmdir', mountpoint], check=True)
                    self.log(f'Removed mount point {mountpoint}')
                except subprocess.CalledProcessError:
                    QMessageBox.warning(self, 'Warning', f'Could not remove directory {mountpoint}. Make sure it is empty and not mounted.')
                    self.log(f'Failed to remove mount point {mountpoint}')
                idx = next((i for i, d in enumerate(self.discos) if d['device_or_file'] == device_or_file and d['mountpoint'] == mountpoint), None)
                if idx is not None:
                    self.remove_disk(idx)
                    self.log(f'Removed file disk {device_or_file} from list')
            QMessageBox.information(self, 'Success', 'Disk deleted.')
            self.log(f'Disk deleted: {device_or_file}')
            self.update_table()
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Failed to delete disk:\n{e}')
            self.log(f'Failed to delete disk {device_or_file}: {e}')

    def open_mount_dir(self, row, col):
        mountpoint = self.table.item(row, 2).text()
        if mountpoint and os.path.exists(mountpoint):
            subprocess.Popen(['xdg-open', mountpoint])
            self.log(f'Opened mount directory: {mountpoint}')

    def show_about(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        about_dialog = QDialog(self)
        about_dialog.setWindowTitle('About VDM')
        layout = QVBoxLayout(about_dialog)
        label = QLabel(
            '<b>VDM</b> (Virtual Disk Manager)<br>'
            'Version 0.1 beta<br>'
            'Author: Esther (<a href="https://github.com/SterTheStar">github.com/SterTheStar</a>)<br>'
            '<br><br>'
            '<b>Source Code:</b> <a href="https://github.com/SterTheStar/VDM">Github</a><br>'
            '<b>License:</b> <a href="#gpl3">GPL v3.0</a><br>'
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
            self.show_full_license()

    def show_full_license(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        gpl_text = '''GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

For the full license, see https://www.gnu.org/licenses/gpl-3.0.html
'''
        dlg = QDialog(self)
        dlg.setWindowTitle('GPL v3.0 License')
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(gpl_text)
        layout.addWidget(text)
        btn = QPushButton('Close')
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.resize(700, 500)
        dlg.exec_()

class RamDiskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Criar RAM Disk')
        self.setModal(True)
        layout = QFormLayout(self)
        # Tamanhos comuns
        self.size_combo = QComboBox()
        tamanhos = ['128M', '256M', '512M', '1G', '2G', '4G']
        self.size_combo.addItems(tamanhos)
        self.size_combo.setEditable(True)
        self.size_combo.setCurrentText('512M')
        # Sugestão de ponto de montagem
        self.mountpoint_combo = QComboBox()
        sugestoes = self.sugerir_mountpoints()
        for s in sugestoes:
            idx = self.mountpoint_combo.count()
            self.mountpoint_combo.addItem(s)
            if os.path.exists(s):
                self.mountpoint_combo.model().item(idx).setEnabled(False)
        self.mountpoint_combo.setEditable(True)
        # Seleciona o primeiro disponível
        for i in range(self.mountpoint_combo.count()):
            if self.mountpoint_combo.model().item(i).isEnabled():
                self.mountpoint_combo.setCurrentIndex(i)
                break
        layout.addRow('Tamanho:', self.size_combo)
        layout.addRow('Ponto de montagem:', self.mountpoint_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def sugerir_mountpoints(self):
        base = '/mnt/ramdisk'
        sugestoes = []
        for i in range(1, 6):
            sugestoes.append(f'{base}{i}')
        return sugestoes

    def get_data(self):
        return self.size_combo.currentText().strip(), self.mountpoint_combo.currentText().strip()

class FileDiskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Criar Disco de Arquivo')
        self.setModal(True)
        layout = QFormLayout(self)
        # Sugestão de arquivo
        self.file_combo = QComboBox()
        arquivos = self.sugerir_arquivos()
        for a in arquivos:
            idx = self.file_combo.count()
            self.file_combo.addItem(a)
            if os.path.exists(a):
                self.file_combo.model().item(idx).setEnabled(False)
        self.file_combo.setEditable(True)
        # Seleciona o primeiro disponível
        for i in range(self.file_combo.count()):
            if self.file_combo.model().item(i).isEnabled():
                self.file_combo.setCurrentIndex(i)
                break
        # Tamanhos comuns
        self.size_combo = QComboBox()
        tamanhos = ['128M', '256M', '512M', '1G', '2G', '4G']
        self.size_combo.addItems(tamanhos)
        self.size_combo.setEditable(True)
        self.size_combo.setCurrentText('1G')
        # Sugestão de ponto de montagem
        self.mountpoint_combo = QComboBox()
        sugestoes = self.sugerir_mountpoints()
        for s in sugestoes:
            idx = self.mountpoint_combo.count()
            self.mountpoint_combo.addItem(s)
            if os.path.exists(s):
                self.mountpoint_combo.model().item(idx).setEnabled(False)
        self.mountpoint_combo.setEditable(True)
        # Seleciona o primeiro disponível
        for i in range(self.mountpoint_combo.count()):
            if self.mountpoint_combo.model().item(i).isEnabled():
                self.mountpoint_combo.setCurrentIndex(i)
                break
        layout.addRow('Arquivo:', self.file_combo)
        layout.addRow('Tamanho:', self.size_combo)
        layout.addRow('Ponto de montagem:', self.mountpoint_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def sugerir_arquivos(self):
        base = '/tmp/disco'
        sugestoes = []
        for i in range(1, 6):
            sugestoes.append(f'{base}{i}.img')
        return sugestoes

    def sugerir_mountpoints(self):
        base = '/mnt/disco'
        sugestoes = []
        for i in range(1, 6):
            sugestoes.append(f'{base}{i}')
        return sugestoes

    def get_data(self):
        return (
            self.file_combo.currentText().strip(),
            self.size_combo.currentText().strip(),
            self.mountpoint_combo.currentText().strip()
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path('icon.ico')))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 