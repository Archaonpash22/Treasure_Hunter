"""Clean up leftover Treasure Hunter processes.

A crashed or hung instance keeps its python process, its QtWebEngine helpers and the console of
start.bat alive, and keeps the tile-cache ports and the DevTools port busy. On start the app closes
every other instance (and its console); on exit it ends its own helper processes so nothing lingers.
"""
import os

try:
    import psutil
except ImportError:  # optional: without it nothing is cleaned up
    psutil = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
_MAIN = os.path.normcase(os.path.join(APP_DIR, 'main.py'))
_START_BAT = os.path.normcase(os.path.join(APP_DIR, 'start.bat'))


def _is_app_process(proc):
    """python running this app's main.py, or the console running its start.bat."""
    try:
        name = (proc.name() or '').lower()
        cmd = proc.cmdline()
    except (psutil.Error, OSError):
        return False
    if name in ('python.exe', 'pythonw.exe', 'python'):
        for arg in cmd[1:]:
            path = arg if os.path.isabs(arg) else os.path.join(_cwd(proc), arg)
            if os.path.normcase(os.path.abspath(path)) == _MAIN:
                return True
    elif name == 'cmd.exe':
        return any(_START_BAT in os.path.normcase(part) for part in cmd)
    return False


def _cwd(proc):
    try:
        return proc.cwd()
    except (psutil.Error, OSError):
        return APP_DIR


def _kill_tree(proc):
    try:
        procs = proc.children(recursive=True) + [proc]
    except psutil.Error:
        procs = [proc]
    for p in procs:
        try:
            p.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(procs, timeout=3)


def close_other_instances():
    """Kill other running instances of the app with their helpers; returns how many were found."""
    if psutil is None or os.environ.get('TREASURE_HUNTER_NO_REAP'):
        return 0
    me = psutil.Process()
    keep = {me.pid} | {p.pid for p in me.parents()}  # our own launcher and console stay
    found = 0
    for proc in psutil.process_iter():
        if proc.pid in keep or not _is_app_process(proc):
            continue
        found += 1
        _kill_tree(proc)
    return found


def end_own_children():
    """Kill helper processes started by this process (QtWebEngine), right before exiting."""
    if psutil is None:
        return
    try:
        children = psutil.Process().children(recursive=True)
    except psutil.Error:
        return
    for p in children:
        try:
            p.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(children, timeout=2)
