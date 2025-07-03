from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton, QDialogButtonBox, QMessageBox, QTabWidget, QWidget, QSizePolicy
from PySide6.QtCore import Qt
import os
import subprocess
import qtawesome as qta

class ModernCreateDiskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Create Virtual Disk')
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setMinimumHeight(320)
        self.setStyleSheet('''
            QDialog { background: #181a1b; color: #e0e0e0; }
            QLabel { color: #e0e0e0; background: transparent; font-size: 16px; }
            QLineEdit, QComboBox { background: #232526; color: #e0e0e0; border-radius: 8px; padding: 10px; font-size: 15px; }
            QCheckBox { color: #e0e0e0; font-size: 15px; }
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #232526; color: #e0e0e0; border-radius: 8px 8px 0 0; padding: 10px 24px; font-size: 16px; margin-right: 8px; min-width: 180px; }
            QTabBar::tab:selected { background: #3a8dde; color: #fff; }
            QComboBox::drop-down { background: transparent; border: none; }
            QComboBox::down-arrow {
                image: url("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0nMTYnIGhlaWdodD0nMTYnIHZpZXdCb3g9JzAgMCAxNiAxNicgZmlsbD0nd2hpdGUnIHhtbG5zPSdodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2Zyc+PHBhdGggZD0nTTQgNmw0IDQgNC00JyBzdHJva2U9J3doaXRlJyBzdHJva2Utd2lkdGg9JzInIGZpbGw9J25vbmUnIHN0cm9rZS1saW5lY2FwPSdyb3VuZCcgLz48L3N2Zz4=");
                width: 18px;
                height: 18px;
            }
        ''')
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)

        self.tabs = QTabWidget()
        self.ram_tab = QWidget()
        self.file_tab = QWidget()
        self.tabs.addTab(self.ram_tab, 'RAM Disk')
        self.tabs.addTab(self.file_tab, 'File Disk')
        layout.addWidget(self.tabs)

        # RAM Disk tab
        ram_layout = QVBoxLayout(self.ram_tab)
        ram_layout.setSpacing(16)
        ram_layout.setContentsMargins(12, 18, 12, 12)
        ram_size_row = QHBoxLayout()
        ram_size_label = QLabel('Size:')
        self.ram_size_combo = QComboBox()
        self.ram_size_combo.addItems(['128M', '256M', '512M', '1G', '2G', '4G'])
        self.ram_size_combo.setEditable(True)
        self.ram_size_combo.setCurrentText('512M')
        ram_size_row.addWidget(ram_size_label)
        ram_size_row.addWidget(self.ram_size_combo)
        ram_layout.addLayout(ram_size_row)
        ram_mp_row = QHBoxLayout()
        ram_mp_label = QLabel('Mount point:')
        self.ram_mountpoint_combo = QComboBox()
        self.ram_mountpoint_combo.setEditable(True)
        for s in self.suggest_ram_mountpoints():
            idx = self.ram_mountpoint_combo.count()
            self.ram_mountpoint_combo.addItem(s)
            if s in self.get_active_ram_mounts():
                self.ram_mountpoint_combo.model().item(idx).setEnabled(False)
        for i in range(self.ram_mountpoint_combo.count()):
            if self.ram_mountpoint_combo.model().item(i).isEnabled():
                self.ram_mountpoint_combo.setCurrentIndex(i)
                break
        ram_mp_row.addWidget(ram_mp_label)
        ram_mp_row.addWidget(self.ram_mountpoint_combo)
        ram_layout.addLayout(ram_mp_row)
        ram_layout.addStretch()

        # File Disk tab
        file_layout = QVBoxLayout(self.file_tab)
        file_layout.setSpacing(16)
        file_layout.setContentsMargins(12, 18, 12, 12)
        file_row = QHBoxLayout()
        file_label = QLabel('File:')
        self.file_combo = QComboBox()
        for a in self.suggest_files():
            idx = self.file_combo.count()
            self.file_combo.addItem(a)
            if os.path.exists(a):
                self.file_combo.model().item(idx).setEnabled(False)
        self.file_combo.setEditable(True)
        for i in range(self.file_combo.count()):
            if self.file_combo.model().item(i).isEnabled():
                self.file_combo.setCurrentIndex(i)
                break
        file_row.addWidget(file_label)
        file_row.addWidget(self.file_combo)
        file_layout.addLayout(file_row)
        file_size_row = QHBoxLayout()
        file_size_label = QLabel('Size:')
        self.file_size_combo = QComboBox()
        self.file_size_combo.addItems(['128M', '256M', '512M', '1G', '2G', '4G'])
        self.file_size_combo.setEditable(True)
        self.file_size_combo.setCurrentText('1G')
        file_size_row.addWidget(file_size_label)
        file_size_row.addWidget(self.file_size_combo)
        file_layout.addLayout(file_size_row)
        file_mp_row = QHBoxLayout()
        file_mp_label = QLabel('Mount point:')
        self.file_mountpoint_combo = QComboBox()
        for s in self.suggest_file_mountpoints():
            idx = self.file_mountpoint_combo.count()
            self.file_mountpoint_combo.addItem(s)
            # Não desabilita por RAM, mas pode adicionar lógica se quiser
        self.file_mountpoint_combo.setEditable(True)
        for i in range(self.file_mountpoint_combo.count()):
            if self.file_mountpoint_combo.model().item(i).isEnabled():
                self.file_mountpoint_combo.setCurrentIndex(i)
                break
        file_mp_row.addWidget(file_mp_label)
        file_mp_row.addWidget(self.file_mountpoint_combo)
        file_layout.addLayout(file_mp_row)
        encrypt_row = QHBoxLayout()
        self.encrypt_checkbox = QCheckBox('Encrypt with LUKS')
        self.encrypt_checkbox.toggled.connect(self.update_fields)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText('Password (required if encrypting)')
        self.password_edit.setMinimumWidth(240)
        self.password_edit.setMaximumWidth(340)
        self.password_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        encrypt_row.addWidget(self.encrypt_checkbox)
        encrypt_row.addSpacing(16)
        encrypt_row.addWidget(self.password_edit, 1)
        file_layout.addLayout(encrypt_row)
        file_layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_fields()

    def update_fields(self):
        # Sempre reserva espaço para o campo de senha, mas só habilita se ativado
        if self.encrypt_checkbox.isChecked():
            self.password_edit.setEnabled(True)
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.password_edit.setPlaceholderText('Password (required if encrypting)')
            self.password_edit.setStyleSheet('')
        else:
            self.password_edit.setEnabled(False)
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.password_edit.setPlaceholderText('')
            self.password_edit.setStyleSheet('background: #232526;')

    def get_data(self):
        if self.tabs.currentIndex() == 0:
            # RAM Disk
            return {
                'type': 'RAM Disk',
                'size': self.ram_size_combo.currentText().strip(),
                'mountpoint': self.ram_mountpoint_combo.currentText().strip()
            }
        else:
            # File Disk
            return {
                'type': 'File Disk',
                'file': self.file_combo.currentText().strip(),
                'size': self.file_size_combo.currentText().strip(),
                'mountpoint': self.file_mountpoint_combo.currentText().strip(),
                'encrypt': self.encrypt_checkbox.isChecked(),
                'password': self.password_edit.text() if self.encrypt_checkbox.isChecked() else None
            }

    def suggest_files(self):
        base = '/tmp/disk'
        return [f'{base}{i}.img' for i in range(1, 6)]

    def suggest_file_mountpoints(self):
        base = '/mnt/disk'
        return [f'{base}{i}' for i in range(1, 6)]

    def suggest_ram_mountpoints(self):
        base = '/mnt/ramdisk'
        return [f'{base}{i}' for i in range(1, 6)]

    def get_active_ram_mounts(self):
        ram_mounts = set()
        try:
            mounts = subprocess.check_output(['mount'], text=True)
            for line in mounts.splitlines():
                if 'type tmpfs' in line:
                    import re
                    m = re.match(r'(.+) on (.+) type tmpfs', line)
                    if m:
                        _, mountpoint = m.groups()
                        ram_mounts.add(mountpoint)
        except Exception:
            pass
        return ram_mounts

    def accept(self):
        # Validação: se encrypt ativado, senha não pode ser vazia
        if self.tabs.currentIndex() == 1 and self.encrypt_checkbox.isChecked():
            if not self.password_edit.text().strip():
                QMessageBox.warning(self, 'Missing Password', 'Please enter a password for LUKS encryption.')
                self.password_edit.setFocus()
                return
        super().accept() 