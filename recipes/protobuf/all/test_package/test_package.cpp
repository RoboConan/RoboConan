#include <cstdlib>
#include <iostream>

#if !defined(CONANTEST_PROTOBUF_LITE)
#include "addressbook.pb.h"
#include <google/protobuf/timestamp.pb.h>
#include <google/protobuf/util/time_util.h>
#else 
#include <google/protobuf/message_lite.h>
#endif

int main()
{

#if !defined(CONANTEST_PROTOBUF_LITE)
	google::protobuf::Timestamp ts;
	google::protobuf::util::TimeUtil::FromString("1972-01-01T10:00:20.021Z", &ts);
	const auto nanoseconds = ts.nanos();
	std::cout << "1972-01-01T10:00:20.021Z in nanoseconds: " << nanoseconds << "\n";
	tutorial::AddressBook address_book;
	auto* person = address_book.add_people();
	person->set_name("RoboConan");
	if (address_book.SerializeAsString().empty()) {
		return EXIT_FAILURE;
	}
#else
	google::protobuf::ShutdownProtobufLibrary();
#endif
	return EXIT_SUCCESS;
}
