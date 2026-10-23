/* Every rank contributes its rank number; rank 0 checks the sum. */
#include <stdio.h>
#include <mpi.h>

int main(int argc, char **argv) {
    int rank, size, sum = -1;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Reduce(&rank, &sum, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);
    if (rank == 0) {
        int expected = size * (size - 1) / 2;
        printf("%d ranks, sum of ranks %d (expected %d)\n", size, sum, expected);
        if (size < 2 || sum != expected) {
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }
    MPI_Finalize();
    return 0;
}
