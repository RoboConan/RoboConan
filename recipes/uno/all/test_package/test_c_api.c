#include <uno/Uno_C_API.h>

static uno_int objective(uno_int number_variables, const double* x,
                         double* value, void* user_data) {
    (void)number_variables;
    (void)user_data;
    *value = (x[0] - 2.) * (x[0] - 2.);
    return 0;
}

static uno_int gradient(uno_int number_variables, const double* x,
                        double* value, void* user_data) {
    (void)number_variables;
    (void)user_data;
    value[0] = 2. * (x[0] - 2.);
    return 0;
}

static uno_int hessian(uno_int number_variables, uno_int number_constraints,
                       uno_int number_nonzeros, const double* x,
                       double objective_multiplier, const double* multipliers,
                       double* values, void* user_data) {
    (void)number_variables;
    (void)number_constraints;
    (void)number_nonzeros;
    (void)x;
    (void)multipliers;
    (void)user_data;
    values[0] = 2. * objective_multiplier;
    return 0;
}

static int solve(const char* preset, const char* linear_solver) {
    void* model = uno_create_unconstrained_model(
        UNO_PROBLEM_NONLINEAR, 1, UNO_ZERO_BASED_INDEXING);
    uno_set_objective(model, UNO_MINIMIZE, objective, gradient);
    const uno_int index = 0;
    uno_set_lagrangian_hessian(model, 1, UNO_LOWER_TRIANGLE,
                               &index, &index, hessian);
    const double initial = 0.;
    uno_set_initial_primal_iterate(model, &initial);

    void* solver = uno_create_solver();
    uno_set_solver_preset(solver, preset);
    if (linear_solver != NULL) {
        uno_set_solver_string_option(solver, "linear_solver", linear_solver);
    }
    uno_optimize(solver, model);
    const int status = uno_get_optimization_status(solver);
    uno_destroy_solver(solver);
    uno_destroy_model(model);
    return status;
}

int main() {
    uno_int major;
    uno_int minor;
    uno_int patch;
    uno_get_version(&major, &minor, &patch);
    if (solve("filtersqp", NULL) != UNO_SUCCESS) {
        return 1;
    }
#ifdef TEST_UNO_MUMPS
    if (solve("ipopt", "MUMPS") != UNO_SUCCESS) {
        return 1;
    }
#endif
}
