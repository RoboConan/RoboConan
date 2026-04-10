#include <hyperion/hyperion.hpp>

int main() {
    using namespace hyperion;
    using Spline = splines::UniformZSplineWithCovariance<Pose3, 4>;

    const auto t0 = Clock::Time{std::chrono::milliseconds(0)};
    const auto dt = Clock::Duration{std::chrono::milliseconds(100)};
    const auto num_segments = 100;

    auto spline = Spline::Identity(t0, dt, num_segments);
}
