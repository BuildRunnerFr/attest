"""Exécution des scripts de contrôle écrits par le modèle.

Deux barrières :
1. garde statique (check, AVANT exécution) : imports en liste blanche ; liste noire de noms
   (exec, eval, open, getattr, vars, globals…) et d'attributs (écritures HTTP, Session/send, os.exec*,
   os.open, écriture/suppression de fichiers…) ; aucun attribut privé ou dunder (sauf __name__) ;
2. garde d'exécution (la vraie défense) : un amorçage (RUNNER, fichier séparé : les numéros de ligne
   du script restent exacts) enveloppe requests/http.client pour refuser toute méthode autre que
   GET/HEAD/OPTIONS, puis installe sys.addaudithook avant d'exécuter le script. Le crochet tue le
   processus (non rattrapable) sur : écriture de fichier, lecture hors des répertoires de Python
   (donc /proc, le dépôt, $HOME…), processus (exec, spawn, fork, system, Popen), ctypes, suppression ou
   renommage de fichiers, connexion ou résolution DNS vers tout autre hôte:port que LAB_URL.
Tout refus → code de sortie non nul → statut "error" (le pipeline réécrit le script).
Le résultat renvoyé est passé par redact.scrub (aucun secret dans le détail ni dans le stderr).
"""
import ast
import json
import os
import subprocess
import sys
import tempfile

from .redact import scrub

ALLOWED_IMPORTS = {"requests", "json", "os", "sys", "re"}
FORBIDDEN_CALLS = {"exec", "eval", "compile", "__import__", "open", "input", "getattr", "setattr", "delattr",
                   "vars", "globals", "locals", "breakpoint", "help", "memoryview", "classmethod", "staticmethod"}
WRITE_METHODS = {"post", "put", "patch", "delete", "request"}
FORBIDDEN_ATTRS = {
    # requests : contournements de la lecture seule
    "send", "Session", "session", "Request", "PreparedRequest", "prepare", "prepare_request", "mount",
    "adapters", "sessions", "api", "packages", "compat", "urllib3", "connection", "connectionpool",
    "poolmanager", "PoolManager", "urlopen", "putrequest", "HTTPConnection", "HTTPConnectionPool",
    "http", "client", "socket", "create_connection", "connect", "sendall", "sendto", "sendmsg", "builtins",
    # os : processus
    "system", "popen", "fork", "forkpty", "kill", "killpg", "abort", "plock", "register_at_fork",
    "setuid", "setgid", "seteuid", "setegid", "setreuid", "setregid", "setresuid", "setresgid",
    "setgroups", "setsid", "setpgid", "setpgrp", "nice", "setpriority", "chroot", "startfile",
    # os : fichiers et descripteurs
    "open", "fdopen", "openpty", "pipe", "pipe2", "dup", "dup2", "memfd_create", "eventfd", "sendfile",
    "write", "writev", "pwrite", "pwritev", "copy_file_range", "splice", "truncate", "ftruncate",
    "posix_fallocate", "lseek", "removedirs", "unlink", "rmdir", "rmtree", "rename", "renames",
    "makedirs", "mkdir", "mkfifo", "mknod", "link", "symlink", "readlink", "chmod", "fchmod",
    "lchmod", "chown", "fchown", "lchown", "chflags", "lchflags", "utime", "chdir", "fchdir", "umask",
    "listdir", "scandir", "walk", "fwalk", "putenv", "unsetenv", "add_dll_directory",
    # sys et introspection
    "modules", "meta_path", "path_hooks", "settrace", "setprofile", "addaudithook", "monitoring",
    "remote_exec", "exc_info", "tb_frame", "tb_next", "f_back", "f_globals", "f_locals", "f_builtins",
    "f_code", "gi_frame", "gi_code", "cr_frame", "ag_frame",
}
# « remove » et « replace » restent permis (str.replace, list.remove) : os.remove/os.replace sont refusés à l'exécution.
FORBIDDEN_PREFIXES = ("exec", "spawn", "posix_spawn", "fork", "kill", "_")
OK_DUNDERS = {"__name__"}


class UnsafeCode(Exception):
    pass


def _bad_attr(a: str) -> bool:
    return a not in OK_DUNDERS and (a in FORBIDDEN_ATTRS or a in WRITE_METHODS or a.startswith(FORBIDDEN_PREFIXES))


def _std_write(node: ast.Attribute) -> bool:
    """sys.stdout.write / sys.stderr.write restent permis."""
    v = node.value
    return (node.attr == "write" and isinstance(v, ast.Attribute) and v.attr in ("stdout", "stderr")
            and isinstance(v.value, ast.Name) and v.value.id == "sys")


def _refuse_attr(a: str):
    if a in WRITE_METHODS:
        raise UnsafeCode(f"méthode HTTP en écriture interdite : .{a}()")
    raise UnsafeCode(f"appel interdit : .{a}()")


def check(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for n in names:
                if n.split(".")[0] not in ALLOWED_IMPORTS:
                    raise UnsafeCode(f"import interdit : {n}")
            if isinstance(node, ast.ImportFrom):           # from os import execv : même liste noire
                for a in node.names:
                    if a.name == "*":
                        raise UnsafeCode(f"import interdit : from {node.module} import *")
                    if a.name in FORBIDDEN_CALLS or _bad_attr(a.name):
                        _refuse_attr(a.name)
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_CALLS:
                raise UnsafeCode(f"appel interdit : {node.id}()")
            if node.id.startswith("__") and node.id not in OK_DUNDERS:
                raise UnsafeCode(f"nom interdit : {node.id}")
        elif isinstance(node, ast.Attribute):
            if _bad_attr(node.attr) and not _std_write(node):
                _refuse_attr(node.attr)
        elif isinstance(node, ast.MatchClass):             # case C(__class__=x) lit un attribut
            for a in node.kwd_attrs:
                if _bad_attr(a):
                    _refuse_attr(a)


# Amorçage exécuté à la place du script : argv[1] = chemin du script.
RUNNER = r'''
import sys, os


def _boot(path):
    import json, re, socket, http.client, requests, requests.sessions
    from urllib.parse import urlsplit

    def deny(what):                     # non rattrapable : le script ne peut pas ignorer un refus
        sys.stderr.write("garde d'exécution : refusé — %s\n" % what)
        sys.stderr.flush()
        os._exit(3)

    u = urlsplit(os.environ.get("LAB_URL", ""))
    host, port = u.hostname or "", u.port or (443 if u.scheme == "https" else 80)
    try:
        addrs = {a[4][0] for a in socket.getaddrinfo(host, port)} | {host}
    except OSError:
        addrs = {host}
    dirs = {sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix, *sys.path}
    try:
        import certifi
        dirs.add(os.path.dirname(certifi.where()))
    except Exception:
        pass
    roots = tuple(os.path.realpath(p).rstrip(os.sep) + os.sep for p in dirs
                  if p and os.path.isdir(p) and os.path.realpath(p) != os.sep)
    mine = {os.path.realpath(path), os.path.realpath(sys.argv[0])}       # pour les tracebacks

    # lecture seule HTTP : seules GET, HEAD, OPTIONS partent
    def ro(method):
        m = method.decode() if isinstance(method, bytes) else str(method)
        if m.upper() not in ("GET", "HEAD", "OPTIONS"):
            deny("méthode HTTP %s (lecture seule)" % m)
    put, send = http.client.HTTPConnection.putrequest, requests.Session.send
    def putrequest(self, method, *a, **k):
        ro(method)
        return put(self, method, *a, **k)
    def session_send(self, request, **k):
        ro(request.method)
        return send(self, request, **k)
    http.client.HTTPConnection.putrequest = putrequest
    requests.Session.send = session_send
    requests.sessions.get_netrc_auth = lambda *a, **k: None       # pas de lecture de ~/.netrc

    W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
    BAN = ("os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.system", "os.kill", "os.killpg",
           "os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.link", "os.symlink",
           "os.truncate", "os.utime", "os.chdir", "os.chflags", "os.lchflags", "os.lchmod", "os.startfile",
           "os.mkfifo", "os.mknod", "os.setxattr", "os.removexattr", "os.add_dll_directory",
           "subprocess.", "ctypes.", "shutil.", "pty.", "marshal.load", "pickle.", "webbrowser.",
           "sys.settrace", "sys.setprofile", "sys.addaudithook",
           "sys.remote_exec", "socket.bind", "socket.sendto", "socket.sendmsg", "socket.sethostname",
           "cpython.remote_debugger_script")
    LOCKED = {"requests", "urllib3", "http", "socket", "ssl"}

    def readable(p):
        if isinstance(p, int):
            return False
        p = os.path.realpath(os.fsdecode(p))
        return p in mine or p.startswith(roots) or not os.path.lexists(p)    # inexistant : rien à lire

    def hook(ev, args):
        if ev == "open":
            p, mode, flags = args
            if (flags or 0) & W or (mode and any(c in mode for c in "wax+")):
                deny("ouverture en écriture de %r" % (p,))
            if not readable(p):
                deny("lecture de %r (hors des répertoires de Python)" % (p,))
        elif ev in ("os.listdir", "os.scandir"):
            if args and args[0] is not None and not readable(args[0]):
                deny("liste du répertoire %r" % (args[0],))
        elif ev == "socket.getaddrinfo":
            h = args[0].decode() if isinstance(args[0], bytes) else args[0]
            if h not in addrs or args[1] not in (None, port, str(port)):
                deny("résolution de %s:%s (seul LAB_URL est joignable)" % (h, args[1]))
        elif ev == "socket.connect":
            a = args[1]
            if not (isinstance(a, tuple) and a[0] in addrs and a[1] == port):
                deny("connexion à %r (seul LAB_URL est joignable)" % (a,))
        elif ev.startswith(("socket.gethostby", "socket.getnameinfo")):
            if args and str(args[0]) not in addrs:
                deny("résolution de %r" % (args[0],))
        elif ev in ("object.__setattr__", "object.__delattr__"):
            o = args[0]
            if isinstance(o, type) and str(getattr(o, "__module__", "")).split(".")[0] in LOCKED:
                deny("modification de %s.%s" % (o.__name__, args[1]))
        elif ev in ("sys._getframe", "sys._current_frames") or ev.startswith(BAN):
            deny("%s%r" % (ev, tuple(str(x)[:80] for x in args)))

    with open(path) as f:
        code = compile(f.read(), "check.py", "exec")
    sys.argv = ["check.py"]
    g = {"__name__": "__main__", "__file__": "check.py", "__builtins__": __builtins__}
    sys.addaudithook(hook)
    return code, g


_c, _g = _boot(sys.argv[1])
del _boot
exec(_c, _g)
'''


def run(code: str, lab_url: str, token: str, timeout: int = 30) -> dict:
    """Exécute le script ; il doit imprimer en dernière ligne un JSON {status, observed, expected, detail}."""
    check(code)
    return scrub(_run(code, lab_url, token, timeout))


def _run(code: str, lab_url: str, token: str, timeout: int) -> dict:
    with tempfile.TemporaryDirectory() as d:
        path, runner = os.path.join(d, "check.py"), os.path.join(d, "runner.py")
        with open(path, "w") as f:
            f.write(code)
        with open(runner, "w") as f:
            f.write(RUNNER)
        env = {"LAB_URL": lab_url, "LAB_TOKEN": token, "PATH": os.environ.get("PATH", ""),
               "NO_PROXY": "127.0.0.1,localhost"}
        p = subprocess.run([sys.executable, "-I", runner, path], capture_output=True, text=True,
                           timeout=timeout, cwd=d, env=env, stdin=subprocess.DEVNULL)
    lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
    if p.returncode != 0 or not lines:
        return {"status": "error", "detail": (p.stderr or p.stdout)[-800:]}
    try:
        res = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"status": "error", "detail": f"sortie non JSON : {lines[-1][:300]}"}
    if not isinstance(res, dict) or res.get("status") not in ("pass", "fail"):
        return {"status": "error", "detail": f"statut invalide : {res}"}
    if res["status"] == "fail" and res.get("observed") in (None, "", [], {}):
        # pas de constat sans valeur constatée : c'est une erreur technique, pas une non-conformité
        return {"status": "error", "detail": f"échec sans valeur constatée — {res.get('detail', '')}"}
    return res
