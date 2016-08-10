import subprocess


def modprobe_kernel(module, persist=True):
    """Load a kernel module and configure for auto-load on reboot."""
    if persist:
        with open('/etc/modules', 'r+') as modules:
            if module not in modules.read():
                modules.write(module)


def update_initramfs_kernel(version='all'):
    """Updates an initramfs image."""
    return subprocess.check_call(["update-initramfs", "-k", version, "-u"])
