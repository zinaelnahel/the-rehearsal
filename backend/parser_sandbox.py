"""Linux parser confinement, applied after trusted imports and before input reads.

Landlock denies filesystem access except read-only runtime libraries, fonts and OCR language data.
Seccomp denies networking, new processes and access to other processes.
Unsupported hosts fail closed when PARSER_SANDBOX=required.
"""
import ctypes as c
import errno
import os
from pathlib import Path
import platform
import sys


def confine():
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'aarch64'):
        raise RuntimeError('Linux sandbox unavailable')
    libc = c.CDLL(None, use_errno=True)
    sec = c.CDLL('libseccomp.so.2', use_errno=True)
    sec.seccomp_init.argtypes = [c.c_uint32]
    sec.seccomp_init.restype = c.c_void_p
    sec.seccomp_syscall_resolve_name.argtypes = [c.c_char_p]
    sec.seccomp_syscall_resolve_name.restype = c.c_int
    sec.seccomp_rule_add.argtypes = [c.c_void_p, c.c_uint32, c.c_int, c.c_uint]
    sec.seccomp_load.argtypes = [c.c_void_p]
    sec.seccomp_release.argtypes = [c.c_void_p]
    if libc.prctl(38, 1, 0, 0, 0):
        raise RuntimeError('no_new_privs unavailable')
    # ABI 3 includes REFER and TRUNCATE; older kernels cannot provide this policy.
    abi = libc.syscall(444, 0, 0, 1)
    if abi < 3:
        raise RuntimeError('Landlock ABI 3 required')
    handled = (1 << 15) - 1
    ruleset_attr = c.c_uint64(handled)
    ruleset = libc.syscall(444, c.byref(ruleset_attr), c.sizeof(ruleset_attr), 0)
    if ruleset < 0:
        raise RuntimeError('Landlock ruleset unavailable')

    class PathRule(c.Structure):
        _pack_ = 1
        _fields_ = [('access', c.c_uint64), ('parent', c.c_int32)]

    try:
        # Never allow /app, /home, /tmp, /proc, or application configuration.
        roots = {str(Path(sys.base_prefix) / 'lib'), '/usr/lib', '/lib', '/lib64',
                 '/usr/share/fonts', '/usr/share/tesseract-ocr'}
        for root in roots:
            if not Path(root).is_dir():
                continue
            fd = os.open(root, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = PathRule((1 << 2) | (1 << 3), fd)  # READ_FILE | READ_DIR
                if libc.syscall(445, ruleset, 1, c.byref(rule), 0):
                    raise RuntimeError('Landlock path rule failed')
            finally:
                os.close(fd)
        if libc.syscall(446, ruleset, 0):
            raise RuntimeError('Landlock confinement failed')
    finally:
        os.close(ruleset)
    ctx = sec.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not ctx:
        raise RuntimeError('Seccomp unavailable')
    try:
        for name in ('socket', 'socketpair', 'connect', 'bind', 'listen', 'accept', 'accept4',
                     'execve', 'execveat', 'fork', 'vfork', 'clone', 'clone3', 'ptrace',
                     'process_vm_readv', 'process_vm_writev', 'pidfd_getfd', 'kill', 'tkill',
                     'tgkill', 'mount', 'umount2', 'unshare', 'setns', 'bpf', 'io_uring_setup'):
            number = sec.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and sec.seccomp_rule_add(ctx, 0x50000 | errno.EPERM, number, 0):
                raise RuntimeError('Seccomp rule failed')
        if sec.seccomp_load(ctx):
            raise RuntimeError('Seccomp confinement failed')
    finally:
        sec.seccomp_release(ctx)
