#include <daqp/daqp.hpp>

int main(void) {
    Eigen::MatrixXd h = Eigen::MatrixXd::Identity(1, 1);
    Eigen::VectorXd f = Eigen::VectorXd::Ones(1);
    Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> a(0, 1);
    Eigen::VectorXd bounds(0);
    EigenDAQPResult result = daqp_solve(h, f, a, bounds, bounds);
    return result.get_primal().size() == 1 ? 0 : 1;
}
