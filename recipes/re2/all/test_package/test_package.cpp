#include <re2/re2.h>

#include <iostream>
#include <cassert>

int main() {
    assert(RE2::FullMatch("hello", "h.*o"));
    assert(!RE2::FullMatch("hello", "e"));
#if defined(EXPECT_ICU)
    assert(RE2::FullMatch("A", R"(\p{Script_Extensions=Latin})"));
#endif
    return 0;
}
