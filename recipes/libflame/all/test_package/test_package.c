#include <FLAME.h>

int main(void) {
    FLA_Obj a;
    FLA_Obj b;
    FLA_Obj c;

    FLA_Init();
    FLA_Obj_create(FLA_DOUBLE, 2, 2, 0, 0, &a);
    FLA_Obj_create_conf_to(FLA_NO_TRANSPOSE, a, &b);
    FLA_Obj_create_conf_to(FLA_NO_TRANSPOSE, a, &c);
    FLA_Set(FLA_ONE, a);
    FLA_Set(FLA_ONE, b);
    FLA_Gemm(FLA_NO_TRANSPOSE, FLA_NO_TRANSPOSE, FLA_ONE, a, b, FLA_ZERO, c);
    FLA_Set_to_identity(c);
    FLA_Chol(FLA_LOWER_TRIANGULAR, c);
    FLA_Obj_free(&c);
    FLA_Obj_free(&b);
    FLA_Obj_free(&a);
    FLA_Finalize();
}
