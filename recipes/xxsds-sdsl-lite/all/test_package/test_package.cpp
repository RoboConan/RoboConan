#include <sdsl/bit_vectors.hpp>
#include <iostream>

int main()
{
    sdsl::bit_vector b(10000000, 0);
    b[8] = 1;
    sdsl::rank_support_v<> rb(&b);
}
