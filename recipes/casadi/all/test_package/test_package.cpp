#include <casadi/casadi.hpp>

#include <algorithm>
#include <cstdio>
#include <cmath>
#include <string>
#include <vector>

namespace {

bool test_nlpsol(const std::string& plugin, const casadi::Dict& options = {}) {
  casadi::SX x = casadi::SX::sym("x");
  casadi::SXDict nlp{{"x", x}, {"f", (x - 2) * (x - 2)}};
  casadi::Function solver = casadi::nlpsol("solver", plugin, nlp, options);
  casadi::DMDict result = solver(casadi::DMDict{{"x0", 0}});
  return std::abs(static_cast<double>(result.at("x")) - 2) < 1e-5
      && std::abs(static_cast<double>(result.at("f"))) < 1e-8;
}

bool test_ccopt() {
  casadi::SX x = casadi::SX::sym("x");
  casadi::SX y = casadi::SX::sym("y");
  casadi::SXDict nlp{{"x", casadi::SX::vertcat({x, y})},
                     {"f", (x - 2) * (x - 2) + (y - 2) * (y - 2)}};
  casadi::Dict options{{"cc_pairs", std::vector<std::vector<long long int>>{{0, 1}}},
                       {"madnlp", casadi::Dict{{"bound_relax_factor", 0.0}}}};
  casadi::Function solver = casadi::nlpsol("solver", "ccopt", nlp, options);
  casadi::DMDict result = solver(casadi::DMDict{{"x0", std::vector<double>{2.5, 3.0}},
                                                {"lbx", std::vector<double>{0.0, 0.0}}});
  std::vector<double> solution = result.at("x").nonzeros();
  return std::abs(std::min(solution[0], solution[1])) < 1e-5
      && std::abs(std::max(solution[0], solution[1]) - 2) < 1e-5
      && std::abs(static_cast<double>(result.at("f")) - 4) < 1e-5;
}

bool test_lacemodelica() {
  casadi::DaeBuilder dae("from_bmo", TEST_BMO_PATH);
  casadi::Function ode = dae.create("ode", {"x"}, {"ode"});
  std::vector<double> result = ode(casadi::DM(std::vector<double>{1, 2})).at(0).nonzeros();
  return result.size() == 2
      && std::abs(result[0] - 1.5) < 1e-12
      && std::abs(result[1] - 0.4) < 1e-12;
}

#if defined(TEST_GRAPHMODEL_ONNX) || defined(TEST_ONNXBACKEND_ORT)
bool test_onnx(const std::string& name, bool symbolic) {
  casadi::MX x = casadi::MX::sym("x");
  casadi::Function affine("affine", {x}, {2 * x + 1});
  std::string model_path = name + ".onnx";
  casadi::GraphBuilder(affine).export_onnx(model_path);
  casadi::Function imported = casadi::GraphBuilder(model_path).create(
      name, casadi::Dict{{"symbolic", symbolic}, {"backend", "ort"}});
  double result = static_cast<double>(imported(casadi::DM(3)).at(0));
  std::remove(model_path.c_str());
  return std::abs(result - 7) < 1e-12;
}
#endif

bool test_bisection() {
  casadi::SX x = casadi::SX::sym("x");
  casadi::SX p = casadi::SX::sym("p");
  casadi::Function residual("residual", {x, p}, {x * x - p});
  casadi::Function solver = casadi::rootfinder("solver", "bisection", residual);
  return std::abs(static_cast<double>(solver(std::vector<casadi::DM>{1, 2}).at(0))
      - std::sqrt(2.0)) < 1e-7;
}

}  // namespace

int main(void) {
  casadi::SX x = casadi::SX::sym("x");
  casadi::Function square("square", {x}, {x * x});
  if (static_cast<double>(square(casadi::DM(3)).at(0)) != 9) return 1;

#ifdef TEST_OPENMP_MAP
  casadi::Function parallel_square = square.map(4, "openmp");
  casadi::DM values = casadi::DM::reshape(casadi::DM(std::vector<double>{1, 2, 3, 4}), 1, 4);
  if (parallel_square(values).at(0).nonzeros() != std::vector<double>{1, 4, 9, 16}) return 1;
#endif

#ifdef TEST_BLAS_BLASFEO
  if (!casadi::has_blas("blasfeo")) return 1;
#endif
#ifdef TEST_NLPSOL_CCOPT
  if (!casadi::has_nlpsol("ccopt") || !test_ccopt()) return 1;
#endif
#ifdef TEST_NLPSOL_CONOPT
  if (!casadi::has_nlpsol("conopt")) return 1;
#endif
#ifdef TEST_NLPSOL_FATROP
  if (!casadi::has_nlpsol("fatrop")) return 1;
#endif
#ifdef TEST_CONIC_HIGHS
  if (!casadi::has_conic("highs")) return 1;
#endif
#ifdef TEST_CONIC_HPIPM
  if (!casadi::has_conic("hpipm")) return 1;
#endif
#ifdef TEST_NLPSOL_IPOPT
  if (!casadi::has_nlpsol("ipopt")) return 1;
#endif
#ifdef TEST_LINSOL_LAPACK
  if (!casadi::has_linsol("lapacklu")) return 1;
#endif
#ifdef TEST_MODELICAPARSER_LACEMODELICA
  if (!casadi::has_modelicaparser("lacemodelica") || !test_lacemodelica()) return 1;
#endif
#ifdef TEST_NLPSOL_MADNLP
  if (!casadi::has_nlpsol("madnlp")) return 1;
#ifdef TEST_NLPSOL_MADNLP_FUNCTIONAL
  if (!test_nlpsol("madnlp")) return 1;
#endif
#endif
#ifdef TEST_CONIC_MOSEK
  if (!casadi::has_conic("mosek")) return 1;
#endif
#ifdef TEST_GRAPHMODEL_ONNX
  if (!casadi::has_graphmodel("onnx") || !test_onnx("symbolic_onnx", true)) return 1;
#endif
#ifdef TEST_ONNXBACKEND_ORT
  if (!casadi::has_onnxbackend("ort") || !test_onnx("runtime_onnx", false)) return 1;
#endif
#ifdef TEST_CONIC_OSQP
  if (!casadi::has_conic("osqp")) return 1;
#endif
#ifdef TEST_CONIC_PIQP
  if (!casadi::has_conic("piqp")) return 1;
#endif
#ifdef TEST_CONIC_PROXQP
  if (!casadi::has_conic("proxqp")) return 1;
#endif
#ifdef TEST_CONIC_QPOASES
  if (!casadi::has_conic("qpoases")) return 1;
#endif
#ifdef TEST_INTEGRATOR_CVODES
  if (!casadi::has_integrator("cvodes")) return 1;
#endif
#ifdef TEST_NLPSOL_UNO
  casadi::Dict uno_options{{"uno", casadi::Dict{{"preset", "filterslp"}}}};
  if (!casadi::has_nlpsol("uno") || !test_nlpsol("uno", uno_options)) return 1;
#endif
#ifdef TEST_ROOTFINDER_BISECTION
  if (!casadi::has_rootfinder("bisection") || !test_bisection()) return 1;
#endif
#ifdef TEST_CONIC_XPRESS
  if (!casadi::has_conic("xpress")) return 1;
#endif
}
