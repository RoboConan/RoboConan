#include <CoinDenseFactorization.hpp>
#include <CoinMpsIO.hpp>
#include <CoinParam.hpp>
#include <CoinUtilsConfig.h>

int main () {
    // Using CoinDenseFactorization to check that LAPACK name mangling is correct
    // and linking succeeds.
    CoinDenseFactorization factorization;
    CoinParamUtils::isCommandLine();

#ifdef COIN_HAS_GLPK
    CoinMpsIO model;
    if (model.readGMPL(TEST_GMPL_PATH, nullptr, true) != 0) {
        return 1;
    }
#endif
}
