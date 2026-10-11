#include <SheenBidi/SheenBidi.h>
#include <string.h>

int main()
{
    const char* text = "abc";
    const SBCodepointSequence sequence = {SBStringEncodingUTF8, (void*)text, strlen(text)};
    SBAlgorithmRef algorithm = SBAlgorithmCreate(&sequence);
}
