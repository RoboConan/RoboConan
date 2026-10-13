#include <gdextension_interface.h>
#include <godot_cpp/variant/vector2.hpp>

int main()
{
    godot::Vector2 vector{1.0, -1.0};
    vector.length();
}
