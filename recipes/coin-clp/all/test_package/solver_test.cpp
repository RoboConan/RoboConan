#include "CbcOrClpParam.hpp"

int main()
{
    CbcOrClpParam parameter;
    return parameter.matches("logLevel") < 0;
}
