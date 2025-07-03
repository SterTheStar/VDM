import os
import sys
import notify2

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

def format_size(size):
    """
    Formata um valor de bytes (int) ou string ('624123k', '1024m', '2g') para MB/GB.
    """
    if isinstance(size, (int, float)):
        mb = float(size) / (1024 * 1024)
        if mb >= 1024:
            gb = mb / 1024
            return f"{gb:.2f} GB"
        else:
            return f"{mb:.0f} MB"
    size_str = str(size).strip().lower()
    if size_str.endswith('g'):
        mb = float(size_str[:-1]) * 1024
    elif size_str.endswith('m'):
        mb = float(size_str[:-1])
    elif size_str.endswith('k'):
        mb = float(size_str[:-1]) / 1024
    elif size_str.isdigit():
        mb = float(size_str) / 1024  # assume KB se só número
    else:
        return size_str  # formato desconhecido, retorna como está
    if mb >= 1024:
        gb = mb / 1024
        return f"{gb:.2f} GB"
    else:
        return f"{mb:.0f} MB"

def get_disk_usage(mountpoint):
    """Return (used_bytes, total_bytes) for the given mountpoint."""
    st = os.statvfs(mountpoint)
    total = st.f_frsize * st.f_blocks
    free = st.f_frsize * st.f_bavail
    used = total - free
    return used, total

def send_notification(title, message, icon=None, urgency=None):
    try:
        notify2.init('VDM')
        if icon is None:
            icon = os.path.join(os.path.dirname(__file__), 'resources', 'vdm.png')
        n = notify2.Notification(title, message, icon)
        if urgency is not None:
            n.set_urgency(urgency)
        else:
            n.set_urgency(notify2.URGENCY_NORMAL)
        n.show()
    except Exception:
        pass 