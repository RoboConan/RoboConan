#include <implot.h>

int main() {
    void (* volatile show_demo)(bool*) = &ImPlot::ShowDemoWindow;
    if (show_demo == nullptr) {
        return 1;
    }

    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImPlot::CreateContext();

#if IMPLOT_VERSION_NUM >= 10000
    ImPlotSpec spec;
    spec.LineColor = ImVec4(1.0F, 0.5F, 0.0F, 1.0F);
    if (spec.LineColor.x != 1.0F) {
        return 1;
    }
#endif

    ImPlot::DestroyContext();
    ImGui::DestroyContext();
    return 0;
}
