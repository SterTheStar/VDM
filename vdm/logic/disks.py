import os
import json
import subprocess

def load_disks(discos_json):
    """Load disks from the JSON file, removendo discos cujo mountpoint não existe."""
    if os.path.exists(discos_json):
        with open(discos_json, 'r') as f:
            discos = json.load(f)
        # Remove discos cujo mountpoint não existe
        filtered = [d for d in discos if d.get('mountpoint') and os.path.exists(d['mountpoint'])]
        if len(filtered) != len(discos):
            save_disks(filtered, discos_json)
        return filtered
    return []

def save_disks(discos, discos_json):
    """Save disks to the JSON file."""
    with open(discos_json, 'w') as f:
        json.dump(discos, f, indent=2)

def add_disk(discos, disk, discos_json):
    """Add a file disk to the list and save."""
    if disk['type'] == 'File':
        discos.append(disk)
        save_disks(discos, discos_json)

def remove_disk(discos, idx, discos_json):
    """Remove a disk by index and save."""
    discos.pop(idx)
    save_disks(discos, discos_json)

def sync_disks_status(discos):
    """Update the status of file disks based on system state, including LUKS encrypted disks."""
    try:
        mounts = subprocess.check_output(['mount'], text=True)
    except Exception:
        mounts = ''
    try:
        losetup = subprocess.check_output(['sudo', 'losetup', '-a'], text=True)
    except Exception:
        losetup = ''
    for disk in discos:
        if disk['type'] == 'File':
            loopdev = None
            if disk.get('encrypted'):
                import os
                luks_name = os.path.basename(disk['device_or_file']) + '_luks'
                luks_path = f'/dev/mapper/{luks_name}'
                if os.path.exists(luks_path):
                    loopdev = luks_path
            else:
                for line in losetup.splitlines():
                    if disk['device_or_file'] in line:
                        import re
                        m = re.match(r'(/dev/loop\d+):', line)
                        if m:
                            loopdev = m.group(1)
                            break
            if loopdev and any(loopdev in mline for mline in mounts.splitlines()):
                disk['status'] = 'Mounted'
            else:
                disk['status'] = 'Unmounted'
    return discos

def size_to_mb(size_str):
    """Convert size string (e.g. 1G, 500M) to MB as int."""
    size_str = size_str.strip().upper()
    if size_str.endswith('G'):
        return int(float(size_str[:-1]) * 1024)
    elif size_str.endswith('M'):
        return int(float(size_str[:-1]))
    else:
        raise ValueError('Size must end with M or G') 