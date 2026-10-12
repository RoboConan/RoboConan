#include <csdp/blockmat.h>
#include <csdp/declarations.h>
#include <csdp/index.h>
#include <csdp/parameters.h>

int main()
{
    struct blockmatrix A;
    A.nblocks = 0;
    triu(A);
}
