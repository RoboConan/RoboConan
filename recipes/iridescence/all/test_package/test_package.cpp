#include <filesystem>
#include <type_traits>
#include <vector>

#include <imgui.h>
#include <ImGuizmo.h>
#include <implot.h>
#include <portable-file-dialogs.h>

#include <glk/cuda_magic_headers.hpp>
#include <glk/html_colors.hpp>
#include <glk/io/jpeg_io.hpp>
#include <glk/io/mesh_io.hpp>
#include <glk/io/png_io.hpp>
#include <glk/path.hpp>
#include <guik/viewer/plot_data.hpp>

int main() {
  static_assert(std::is_pointer_v<decltype(&pfd::settings::available)>);

  ImGui::CreateContext();
  ImPlot::CreateContext();
  (void)ImGuizmo::IsUsing();

  guik::LinePlotStyle line_style;
  line_style.apply();
  guik::ScatterPlotStyle scatter_style;
  scatter_style.apply();

  const auto color = glk::html_color(glk::COLORNAME::AliceBlue);
  if (color.size() != 4) {
    return 1;
  }

  glk::set_data_path(IRIDESCENCE_TEST_DATA_DIR);
  const auto data_path = std::filesystem::path(glk::get_data_path());
  if (!std::filesystem::exists(data_path / "shader" / "rainbow.vert")) {
    return 2;
  }

  int width = 0;
  int height = 0;
  std::vector<unsigned char> bytes;
  if (glk::load_png("does-not-exist.png", width, height, bytes) ||
      glk::load_jpeg("does-not-exist.jpg", width, height, bytes) ||
      glk::load_mesh_model("does-not-exist.obj")) {
    return 3;
  }

  ImPlot::DestroyContext();
  ImGui::DestroyContext();
  return 0;
}
