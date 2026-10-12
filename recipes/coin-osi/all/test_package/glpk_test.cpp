#include <cmath>

#include <CoinPackedVector.hpp>
#include <OsiGlpkSolverInterface.hpp>

int main()
{
    OsiGlpkSolverInterface solver;
    CoinPackedVector column;
    solver.addCol(column, 0.0, solver.getInfinity(), 1.0);

    CoinPackedVector row;
    row.insert(0, 1.0);
    solver.addRow(row, 1.0, solver.getInfinity());
    solver.initialSolve();

    return solver.isProvenOptimal() && std::abs(solver.getColSolution()[0] - 1.0) < 1e-9 ? 0 : 1;
}
