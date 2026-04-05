#include <sym/pose3.h>

#ifdef HAVE_SYMFORCE_OPT
#include <symforce/opt/factor.h>
#include <symforce/opt/key.h>
#include <symforce/opt/optimizer.h>
#include <Eigen/Core>
#include <Eigen/SparseCore>
#endif

#include <iostream>

int main() {
  const sym::Pose3d a{};
  const sym::Pose3d b = a * a;
  std::cout << "a = " << a << "\n";

#ifdef HAVE_SYMFORCE_OPT
  std::vector<sym::Factord> factors;
  factors.push_back(sym::Factord::Hessian(
      [](const Eigen::Vector3d& x, Eigen::VectorXd* const res,
         Eigen::SparseMatrix<double>* const jac, Eigen::SparseMatrix<double>* const hess,
         Eigen::VectorXd* const rhs) {
        if (res) {
          *res = x;
        }
        if (jac) {
          *jac = Eigen::MatrixXd::Identity(3, 3).sparseView();
        }
        if (hess) {
          *hess = Eigen::MatrixXd::Identity(3, 3).sparseView();
        }
        if (rhs) {
          *rhs = x;
        }
      },
      {sym::Key{'x', 0}}));

  sym::Optimizerd optimizer(sym::DefaultOptimizerParams(), factors);
  std::cout << "Optimizer created with " << optimizer.Factors().size() << " factors.\n";
#endif
}
