"""Load every shared library the package under test installs.

A repack copies files without linking anything, so a library whose
dependencies are missing from the package's run requirements only fails
when a user loads it.

Intel's libraries resolve symbols from each other (e.g. oneDAL core needs its
threading layer, MKL kernels need an interface layer), so they are loaded
with global visibility and retried until a pass makes no progress; whatever
is left cannot be loaded in any order. Libraries matching a SKIP substring
need something the test environment does not provide (a SYCL device, MPI).
Some libraries take their symbols from another package's library that the
application loads first (onemkl-sycl-* from MKL, dal-gpu from oneDAL core);
a +LIBRARY argument (relative to the library directory) loads it too, in
the same retry loop.

Usage: python load_libs.py [+LIBRARY ...] [SKIP_SUBSTRING ...]
"""
import ctypes
import glob
import json
import os
import sys

WIN = sys.platform == "win32"
prefix = os.environ.get("PREFIX", sys.prefix)
name = os.environ["PKG_NAME"]
skip = [a for a in sys.argv[1:] if not a.startswith("+")]
preload = [a[1:] for a in sys.argv[1:] if a.startswith("+")]

metas = [m for m in glob.glob(os.path.join(prefix, "conda-meta", f"{name}-*.json"))
         if json.load(open(m))["name"] == name]
assert len(metas) == 1, f"conda-meta for {name}: {metas}"
files = json.load(open(metas[0]))["files"]

if WIN:
    os.add_dll_directory(os.path.join(prefix, "Library", "bin"))
    libs = [f for f in files if f.lower().endswith(".dll")]
    mode = 0
else:
    # every real consumer is a C++ program that already has the C++ runtime
    # loaded, and some upstream libraries rely on that instead of linking it
    ctypes.CDLL(os.path.join(prefix, "lib", "libstdc++.so.6"), mode=ctypes.RTLD_GLOBAL)
    libs = [f for f in files if ".so" in os.path.basename(f)]
    mode = os.RTLD_LAZY | os.RTLD_GLOBAL

assert libs, f"{name} installs no shared libraries"

libdir = "Library/bin" if WIN else "lib"
pending = [f"{libdir}/{lib}" for lib in preload]
for lib in sorted(libs):
    if any(s in os.path.basename(lib) for s in skip):
        print("skip", lib)
    else:
        pending.append(lib)

errors = {}
progress = True
while pending and progress:
    progress = False
    for lib in list(pending):
        try:
            ctypes.CDLL(os.path.join(prefix, lib), mode=mode)
        except OSError as e:
            errors[lib] = e
        else:
            print("ok  ", lib)
            pending.remove(lib)
            progress = True

for lib in pending:
    print("FAIL", lib, errors[lib])
if pending:
    sys.exit(f"{len(pending)} of {len(libs)} libraries failed to load: {pending}")
