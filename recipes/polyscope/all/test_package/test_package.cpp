#include <polyscope/polyscope.h>
#include <polyscope/transformation_gizmo.h>
#if POLYSCOPE_TEST_BACKEND_GLFW
#include <polyscope/render/opengl/gl_engine_glfw.h>
#endif
#if POLYSCOPE_TEST_BACKEND_EGL
#include <polyscope/render/opengl/gl_engine_egl.h>
#endif

#include <iostream>

int main() {
    std::cout << "A random number: " << polyscope::randomUnit() << std::endl;
#if POLYSCOPE_TEST_BACKEND_MOCK
    polyscope::options::usePrefsFile = false;
    polyscope::init("openGL_mock");
    glm::mat4 transform{1.f};
    auto* gizmo = polyscope::addTransformationGizmo("imguizmo", &transform);
    gizmo->setEnabled(true);
    gizmo->setAllowScaling(true);
    gizmo->setAllowNonUniformScaling(false);
    polyscope::frameTick();
    gizmo->setAllowNonUniformScaling(true);
    polyscope::frameTick();

    bool entered_nested_context = false;
    polyscope::pushContext([&entered_nested_context]() {
        entered_nested_context = true;
        polyscope::popContext();
    }, false);
    if (!entered_nested_context) {
        return 1;
    }
    polyscope::shutdown();
#endif
}
