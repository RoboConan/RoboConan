%module python_stubs

%stubcode %{
def package_smoke() -> None: ...
%}

%exception {
    (void)$isvoid;
    $action
}

%inline %{
void no_result(void) {}
int result(void) { return 1; }
%}
