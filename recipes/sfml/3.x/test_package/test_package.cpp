#if defined(TEST_SFML_System)
#include <SFML/System/Version.hpp>
#elif defined(TEST_SFML_Window)
#include <SFML/Window/WindowBase.hpp>
#elif defined(TEST_SFML_Graphics)
#include <SFML/Graphics/Font.hpp>
#include <SFML/Graphics/Image.hpp>
#include <SFML/Graphics/Text.hpp>
#elif defined(TEST_SFML_Network)
#include <SFML/Network/Packet.hpp>
#elif defined(TEST_SFML_Audio)
#include <SFML/Audio/SoundBuffer.hpp>
#endif

#include <cstdint>

int main()
{
#if defined(TEST_SFML_System)
    return sf::version().major == 3 ? 0 : 1;
#elif defined(TEST_SFML_Window)
    sf::WindowBase window;
    return window.getNativeHandle() == sf::WindowHandle{} ? 0 : 1;
#elif defined(TEST_SFML_Graphics)
    const sf::Image image({1, 1});
    const sf::Font font;
    const sf::Text text(font);
    return image.getSize() == sf::Vector2u{1, 1} && text.getString().isEmpty() ? 0 : 1;
#elif defined(TEST_SFML_Network)
    sf::Packet packet;
    packet << std::uint32_t{42};
    return packet.getDataSize() == sizeof(std::uint32_t) ? 0 : 1;
#elif defined(TEST_SFML_Audio)
    const sf::SoundBuffer buffer;
    return buffer.getSampleCount() == 0 ? 0 : 1;
#endif
}
