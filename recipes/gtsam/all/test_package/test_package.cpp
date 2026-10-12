#include <gtsam/config.h>
#include <gtsam/geometry/Rot2.h>
#include <gtsam/inference/Symbol.h>
#include <gtsam/slam/PriorFactor.h>
#ifdef TEST_BOOST_SERIALIZATION
#include <gtsam/base/serialization.h>
#elif GTSAM_ENABLE_BOOST_SERIALIZATION
#error "GTSAM Boost serialization setting does not match the package option"
#endif
#ifdef TEST_CEPHES
#include <gtsam/3rdparty/cephes/cephes.h>
#endif
#ifdef TEST_CUDA
#include <gtsam/base/cuda/DeviceArray.h>
#ifndef GTSAM_ENABLE_CUDA
#error "GTSAM CUDA usage requirements were not propagated"
#endif
#endif
#ifdef TEST_CUDSS
#ifndef GTSAM_ENABLE_CUDSS
#error "GTSAM cuDSS usage requirements were not propagated"
#endif
#endif
#ifdef TEST_MKL
#ifndef GTSAM_USE_EIGEN_MKL
#error "GTSAM was not configured to use MKL"
#endif
#endif
#ifdef TEST_MOSEK
#ifndef GTSAM_USE_MOSEK
#error "GTSAM was not configured to use MOSEK"
#endif
#endif

using namespace gtsam;

const double degree = M_PI / 180;

int main() {

  Rot2 prior = Rot2::fromAngle(30 * degree);
  prior.print("30 degrees in radians is");
  noiseModel::Isotropic::shared_ptr model = noiseModel::Isotropic::Sigma(1, 1 * degree);
  Symbol key('x',1);
  PriorFactor<Rot2> factor(key, prior, model);

#ifdef TEST_CEPHES
  if (gtsam_cephes_Gamma(5.0) != 24.0) {
    return 1;
  }
#endif

  return 0;
}
