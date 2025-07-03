from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox, QPushButton, QVBoxLayout, QTextEdit, QCheckBox, QLabel

class RamDiskDialog(QDialog):
    """Dialog for creating a RAM disk."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Create RAM Disk')
        self.setModal(True)
        layout = QFormLayout(self)
        # Common sizes
        self.size_combo = QComboBox()
        sizes = ['128M', '256M', '512M', '1G', '2G', '4G']
        self.size_combo.addItems(sizes)
        self.size_combo.setEditable(True)
        self.size_combo.setCurrentText('512M')
        # Mount point suggestions
        self.mountpoint_combo = QComboBox()
        suggestions = self.suggest_mountpoints()
        # Detecta mountpoints de RAM disks ativos
        import subprocess
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
        for s in suggestions:
            idx = self.mountpoint_combo.count()
            self.mountpoint_combo.addItem(s)
            if s in ram_mounts:
                self.mountpoint_combo.model().item(idx).setEnabled(False)
        self.mountpoint_combo.setEditable(True)
        for i in range(self.mountpoint_combo.count()):
            if self.mountpoint_combo.model().item(i).isEnabled():
                self.mountpoint_combo.setCurrentIndex(i)
                break
        layout.addRow('Size:', self.size_combo)
        layout.addRow('Mount point:', self.mountpoint_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def suggest_mountpoints(self):
        base = '/mnt/ramdisk'
        return [f'{base}{i}' for i in range(1, 6)]

    def get_data(self):
        return self.size_combo.currentText().strip(), self.mountpoint_combo.currentText().strip()

class FileDiskDialog(QDialog):
    """Dialog for creating a file-based disk."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Create File Disk')
        self.setModal(True)
        layout = QFormLayout(self)
        # File suggestions
        self.file_combo = QComboBox()
        files = self.suggest_files()
        for a in files:
            idx = self.file_combo.count()
            self.file_combo.addItem(a)
            import os
            if os.path.exists(a):
                self.file_combo.model().item(idx).setEnabled(False)
        self.file_combo.setEditable(True)
        for i in range(self.file_combo.count()):
            if self.file_combo.model().item(i).isEnabled():
                self.file_combo.setCurrentIndex(i)
                break
        # Common sizes
        self.size_combo = QComboBox()
        sizes = ['128M', '256M', '512M', '1G', '2G', '4G']
        self.size_combo.addItems(sizes)
        self.size_combo.setEditable(True)
        self.size_combo.setCurrentText('1G')
        # Mount point suggestions
        self.mountpoint_combo = QComboBox()
        suggestions = self.suggest_mountpoints()
        # Detecta mountpoints de RAM disks ativos
        import subprocess
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
        for s in suggestions:
            idx = self.mountpoint_combo.count()
            self.mountpoint_combo.addItem(s)
            if s in ram_mounts:
                self.mountpoint_combo.model().item(idx).setEnabled(False)
        self.mountpoint_combo.setEditable(True)
        for i in range(self.mountpoint_combo.count()):
            if self.mountpoint_combo.model().item(i).isEnabled():
                self.mountpoint_combo.setCurrentIndex(i)
                break
        # Encryption option
        self.encrypt_checkbox = QCheckBox('Encrypt this disk (LUKS)')
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText('Password (required if encrypting)')
        layout.addRow('File:', self.file_combo)
        layout.addRow('Size:', self.size_combo)
        layout.addRow('Mount point:', self.mountpoint_combo)
        layout.addRow(self.encrypt_checkbox)
        layout.addRow(QLabel('Password:'), self.password_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.encrypt_checkbox.toggled.connect(self.password_edit.setEnabled)
        self.password_edit.setEnabled(False)

    def suggest_files(self):
        base = '/tmp/disk'
        return [f'{base}{i}.img' for i in range(1, 6)]

    def suggest_mountpoints(self):
        base = '/mnt/disk'
        return [f'{base}{i}' for i in range(1, 6)]

    def get_data(self):
        return (
            self.file_combo.currentText().strip(),
            self.size_combo.currentText().strip(),
            self.mountpoint_combo.currentText().strip(),
            self.encrypt_checkbox.isChecked(),
            self.password_edit.text() if self.encrypt_checkbox.isChecked() else None
        )

def show_full_license(parent):
    """Show the full GPL v3.0 license in a scrollable dialog, loading from resources/LICENSE."""
    import os
    dlg = QDialog(parent)
    dlg.setWindowTitle('GPL v3.0 License')
    layout = QVBoxLayout(dlg)
    text = QTextEdit()
    text.setReadOnly(True)
    # Lê o arquivo LICENSE da pasta resources
    license_path = os.path.join(os.path.dirname(__file__), 'resources', 'LICENSE')
    try:
        with open(license_path, 'r') as f:
            gpl_text = f.read()
    except Exception:
        gpl_text = 'License file not found.'
    text.setPlainText(gpl_text)
    layout.addWidget(text)
    btn = QPushButton('Close')
    btn.clicked.connect(dlg.accept)
    layout.addWidget(btn)
    dlg.resize(700, 500)
    dlg.exec_() 