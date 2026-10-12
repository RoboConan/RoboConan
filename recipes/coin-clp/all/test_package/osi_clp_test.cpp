#include "OsiClpSolverInterface.hpp"

int main(int argc, const char *argv[])
{
    if (argc < 2) {
        return 1;
    }
    OsiClpSolverInterface solver;
    return solver.readMps(argv[1]);
}
