const path = require("path");

const wasmDir = path.resolve(process.argv[2]);
const createCasadi = require(path.join(wasmDir, "casadi.js"));

(async () => {
  const casadi = await createCasadi();
  const x = casadi.SX.sym("x");
  const twice = casadi.Function("twice", [x], [casadi.plus(x, x)]);
  const result = twice(casadi.DM(4)).nonzeros();
  if (result.length !== 1 || result[0] !== 8) {
    throw new Error(`unexpected result: ${result}`);
  }

  await casadi.load_linsol("qr");
  const matrix = casadi.DM([[1, 0], [0, 2]]);
  const solver = casadi.Linsol("solver", "qr", matrix.sparsity());
  const solution = solver.solve(matrix, casadi.DM([6, 8])).nonzeros();
  if (solution.length !== 2 || solution[0] !== 6 || solution[1] !== 4) {
    throw new Error(`unexpected linear solution: ${solution}`);
  }
})();
