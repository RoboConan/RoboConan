#if __has_include(<gdextension_interface.h>)
#include <gdextension_interface.h>
#else
#include <gdnative/vector2.h>
#endif

int main()
{
#if __has_include(<gdextension_interface.h>)
  GDExtensionInitialization initialization;
#else
  godot_vector2 vector;
#endif
  return 0;
}
