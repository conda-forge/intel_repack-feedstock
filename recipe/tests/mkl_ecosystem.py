"""Check that numpy and scipy, as conda-forge ships them, work on this mkl.

They come from conda-forge built with GCC/gfortran and reach MKL through the
libblas/liblapack "mkl" variant, so this is how most users load MKL.
"""
import os

import numpy as np
import scipy.linalg
import scipy.linalg.blas
import scipy.linalg.lapack
from threadpoolctl import threadpool_info

print("MKL_INTERFACE_LAYER =", os.environ.get("MKL_INTERFACE_LAYER"))

mkl = [i for i in threadpool_info() if i.get("internal_api") == "mkl"]
assert mkl, f"numpy is not using MKL: {threadpool_info()}"
print("threadpoolctl:", mkl)
expected = os.environ.get("PKG_VERSION")
if expected:
    assert mkl[0]["version"].startswith(".".join(expected.split(".")[:2])), mkl

rng = np.random.default_rng(0)
a = rng.standard_normal((200, 200))
b = rng.standard_normal((200, 3))

x = np.linalg.solve(a, b)
assert np.allclose(a @ x, b)

u, s, vt = np.linalg.svd(a)
assert np.allclose((u * s) @ vt, a)

h = a + 1j * rng.standard_normal((200, 200))
h = h + h.conj().T
w, v = scipy.linalg.eigh(h)
assert np.allclose(h @ v, v * w)

# complex BLAS through scipy; mkl_layers.py checks the calling convention
zx = np.array([1 + 2j, 3 - 1j])
zy = np.array([2 - 1j, 1 + 4j])
assert scipy.linalg.blas.zdotc(zx, zy) == np.vdot(zx, zy) == -1 + 8j

lu, piv, info = scipy.linalg.lapack.dgetrf(a)
assert info == 0
p, l, u = scipy.linalg.lu(a)
assert np.allclose(p @ l @ u, a)

print("numpy", np.__version__, "scipy", scipy.__version__, "OK")
