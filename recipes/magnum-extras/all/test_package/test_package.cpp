#include <iostream>

#include "Magnum/Math/Vector2.h"
#include "Magnum/Ui/AbstractUserInterface.h"
#include "Magnum/versionExtras.h"

int main() {
    Magnum::Ui::AbstractUserInterface ui{Magnum::Vector2i{800, 600}};
    std::cout << MAGNUMEXTRAS_VERSION_YEAR << '.' << MAGNUMEXTRAS_VERSION_MONTH << '\n';
}
