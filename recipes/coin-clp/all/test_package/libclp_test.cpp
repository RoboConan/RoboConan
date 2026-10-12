#include "ClpSimplex.hpp"

int main(int argc, const char *argv[])
{
    if (argc < 2) {
        return 1;
    }
    ClpSimplex model;
    return model.readMps(argv[1]);
}
