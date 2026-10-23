/* Link against oneMKL (shared or static) and check a computed result. */
#include <stdio.h>
#include <mkl.h>

int main(void) {
    /* C = A @ B, row-major 2x2 */
    double a[] = {1, 2, 3, 4};
    double b[] = {5, 6, 7, 8};
    double c[4] = {0};
    const double expected[] = {19, 22, 43, 50};
    char version[256];

    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, 2, 2, 2,
                1.0, a, 2, b, 2, 0.0, c, 2);
    for (int i = 0; i < 4; ++i) {
        if (c[i] != expected[i]) {
            printf("cblas_dgemm: c[%d] = %g, expected %g\n", i, c[i], expected[i]);
            return 1;
        }
    }

    mkl_get_version_string(version, sizeof(version));
    printf("OK %s\n", version);
    return 0;
}
