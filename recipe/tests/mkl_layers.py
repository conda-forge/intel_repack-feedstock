"""Exercise libmkl_rt through every interface and threading layer it can select.

libmkl_rt picks its layers at runtime from MKL_INTERFACE_LAYER and
MKL_THREADING_LAYER, and aborts the process if the matching library is
missing. Each combination therefore runs in its own subprocess.

For every combination the child checks results that depend on the layer
actually behaving as named:
  * dgemm_   - basic Fortran BLAS call
  * dgetrf_  - the pivot array is written with the layer's integer width,
               so an LP64 library behind an ILP64 request gives wrong pivots
  * zdotc_   - complex-valued function: GNU layers return the value,
               Intel layers write it through a hidden first argument
"""
import ctypes
import os
import subprocess
import sys

WIN = sys.platform == "win32"

INTERFACES = ["LP64", "ILP64"] + ([] if WIN else ["GNU,LP64", "GNU,ILP64"])
THREADING = ["SEQUENTIAL", "INTEL", "TBB"] + ([] if WIN else ["GNU"])


class Complex(ctypes.Structure):
    _fields_ = [("re", ctypes.c_double), ("im", ctypes.c_double)]


def load_rt():
    prefix = os.environ.get("PREFIX", sys.prefix)
    if WIN:
        libdir = os.path.join(prefix, "Library", "bin")
        os.add_dll_directory(libdir)
        return ctypes.CDLL(os.path.join(libdir, "mkl_rt.3.dll"))
    return ctypes.CDLL(os.path.join(prefix, "lib", "libmkl_rt.so.3"))


def ref(ctype, value):
    return ctypes.byref(ctype(value))


def child(interface, threading):
    rt = load_rt()
    int_t = ctypes.c_int64 if "ILP64" in interface else ctypes.c_int32
    dbl = ctypes.c_double

    buf = ctypes.create_string_buffer(256)
    rt.MKL_Get_Version_String(buf, len(buf))
    version = buf.value.decode()
    expected = os.environ.get("PKG_VERSION")
    if expected:
        major_minor = ".".join(expected.split(".")[:2])
        assert major_minor in version, f"{version!r} is not {expected}"

    # C = A @ B, column-major 2x2
    a = (dbl * 4)(1, 3, 2, 4)
    b = (dbl * 4)(5, 7, 6, 8)
    c = (dbl * 4)()
    n = ref(int_t, 2)
    rt.dgemm_(b"N", b"N", n, n, n, ref(dbl, 1.0), a, n, b, n, ref(dbl, 0.0), c, n)
    assert list(c) == [19, 43, 22, 50], f"dgemm_: {list(c)}"

    # Largest entry of the first column is in row 3, so ipiv[0] == 3 (1-based)
    m = (dbl * 9)(1, 2, 4, 2, 5, 9, 3, 8, 16)
    ipiv = (int_t * 3)()
    info = int_t(-1)
    three = ref(int_t, 3)
    rt.dgetrf_(three, three, m, three, ipiv, ctypes.byref(info))
    assert info.value == 0, f"dgetrf_ info={info.value}"
    assert list(ipiv)[0] == 3, f"dgetrf_ pivots {list(ipiv)}"

    # conj([1+2j, 3-1j]) . [2-1j, 1+4j] = (1-2j)(2-1j) + (3+1j)(1+4j) = -1+8j
    x = (Complex * 2)(Complex(1, 2), Complex(3, -1))
    y = (Complex * 2)(Complex(2, -1), Complex(1, 4))
    one = ref(int_t, 1)
    two = ref(int_t, 2)
    if "GNU" in interface:
        rt.zdotc_.restype = Complex
        res = rt.zdotc_(two, x, one, y, one)
    else:
        res = Complex()
        rt.zdotc_(ctypes.byref(res), two, x, one, y, one)
    assert (res.re, res.im) == (-1.0, 8.0), f"zdotc_: {res.re}{res.im:+}j"

    print(f"ok  {interface:<10} {threading:<10} {version}")


def main():
    failed = []
    for interface in INTERFACES:
        for threading in THREADING:
            env = dict(os.environ,
                       MKL_INTERFACE_LAYER=interface,
                       MKL_THREADING_LAYER=threading)
            proc = subprocess.run(
                [sys.executable, __file__, interface, threading],
                env=env, capture_output=True, text=True)
            sys.stdout.write(proc.stdout)
            if proc.returncode != 0:
                failed.append((interface, threading))
                print(f"FAIL {interface:<10} {threading:<10} exit {proc.returncode}")
                sys.stdout.write(proc.stderr)
    if failed:
        sys.exit(f"{len(failed)} layer combination(s) failed: {failed}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        child(*sys.argv[1:])
    else:
        main()
