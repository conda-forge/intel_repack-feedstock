"""Check that dnrm2 doesn't depend on how its input is aligned in memory.

oneMKL 2026.2.0 sped up dnrm2 and made its result depend on the address of
the vector: the same values copied to a different offset within a 64-byte
line gave a norm that differed in the last bit, which broke reproducibility
downstream (intel_repack-feedstock#149). Each threading layer runs in its
own subprocess, as libmkl_rt fixes the layer on first use.

For every size the child copies one vector to each of the 8 double-sized
offsets within a 64-byte line, calls dnrm2_ (Fortran) and cblas_dnrm2 on
each copy, requires all results to be bit-identical, and checks the value
against math.dist.
"""
import ctypes
import math
import os
import random
import struct
import subprocess
import sys

WIN = sys.platform == "win32"

THREADING = ["SEQUENTIAL", "INTEL", "TBB"] + ([] if WIN else ["GNU"])
# small sizes take the unthreaded path, large ones get split across threads
SIZES = [1, 7, 8, 9, 20, 33, 64, 1000, 100_003, 1_000_000]
DBL = ctypes.sizeof(ctypes.c_double)
LINE = 64


def load_rt():
    prefix = os.environ.get("PREFIX", sys.prefix)
    if WIN:
        libdir = os.path.join(prefix, "Library", "bin")
        os.add_dll_directory(libdir)
        return ctypes.CDLL(os.path.join(libdir, "mkl_rt.3.dll"))
    return ctypes.CDLL(os.path.join(prefix, "lib", "libmkl_rt.so.3"))


def bits(x):
    return struct.pack("<d", x).hex()


def child(threading):
    rt = load_rt()
    dbl = ctypes.c_double
    ptr = ctypes.POINTER(dbl)
    rt.dnrm2_.restype = dbl
    rt.dnrm2_.argtypes = [ctypes.POINTER(ctypes.c_int32), ptr,
                          ctypes.POINTER(ctypes.c_int32)]
    rt.cblas_dnrm2.restype = dbl
    rt.cblas_dnrm2.argtypes = [ctypes.c_int32, ptr, ctypes.c_int32]

    rng = random.Random(149)
    failures = []
    for n in SIZES:
        values = [rng.gauss(0, 1) for _ in range(n)]
        expected = math.dist(values, [0.0] * n)
        buf = (dbl * (n + 2 * LINE // DBL))()
        base = (-ctypes.addressof(buf) // DBL) % (LINE // DBL)
        nn, inc = ctypes.c_int32(n), ctypes.c_int32(1)
        results = {"dnrm2_": {}, "cblas_dnrm2": {}}
        for off in range(LINE // DBL):
            start = base + off
            buf[start:start + n] = values
            x = ctypes.cast(ctypes.byref(buf, start * DBL), ptr)
            for name, value in [
                ("dnrm2_", rt.dnrm2_(ctypes.byref(nn), x, ctypes.byref(inc))),
                ("cblas_dnrm2", rt.cblas_dnrm2(n, x, 1)),
            ]:
                results[name].setdefault(bits(value), []).append(off)
                if not math.isclose(value, expected, rel_tol=1e-13):
                    failures.append(f"{name} n={n} offset={off}: "
                                    f"{value!r} != {expected!r}")
        for name, seen in results.items():
            if len(seen) > 1:
                detail = ", ".join(
                    f"{struct.unpack('<d', bytes.fromhex(b))[0]!r} at offsets {o}"
                    for b, o in seen.items())
                failures.append(f"{name} n={n} depends on alignment: {detail}")
    if failures:
        sys.exit("\n".join(failures))
    print(f"ok  {threading:<10} threads={rt.MKL_Get_Max_Threads()}")


def main():
    failed = []
    for threading in THREADING:
        env = dict(os.environ, MKL_THREADING_LAYER=threading)
        proc = subprocess.run([sys.executable, __file__, threading],
                              env=env, capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            failed.append(threading)
            print(f"FAIL {threading:<10} exit {proc.returncode}")
            sys.stdout.write(proc.stderr)
    if failed:
        sys.exit(f"dnrm2 failed with threading layer(s): {failed}")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        child(sys.argv[1])
    else:
        main()
