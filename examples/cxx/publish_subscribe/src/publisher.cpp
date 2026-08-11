// Copyright (c) 2024 Contributors to the Eclipse Foundation
//
// See the NOTICE file(s) distributed with this work for additional
// information regarding copyright ownership.
//
// This program and the accompanying materials are made available under the
// terms of the Apache Software License 2.0 which is available at
// https://www.apache.org/licenses/LICENSE-2.0, or the MIT license
// which is available at https://opensource.org/licenses/MIT.
//
// SPDX-License-Identifier: Apache-2.0 OR MIT

#if 1
// Recommended compiler flags (enable in your build system):
//   -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wsign-conversion
// For AUTOSAR / MISRA compliance enable static analysis (clang-tidy, cppcheck)
// and configure checks for MISRA C++ and AUTOSAR rulesets.
// Example clang-tidy invocation (CI):
//   clang-tidy -checks='*,misc-misra*' -- <compile-commands>
// File-level pragmas below enable common warnings with Clang/GCC for this file.
#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic warning "-Wall"
#pragma clang diagnostic warning "-Wextra"
#pragma clang diagnostic warning "-Wshadow"
#pragma clang diagnostic warning "-Wconversion"
#pragma clang diagnostic warning "-Wsign-conversion"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic warning "-Wall"
#pragma GCC diagnostic warning "-Wextra"
#pragma GCC diagnostic warning "-Wshadow"
#pragma GCC diagnostic warning "-Wconversion"
#pragma GCC diagnostic warning "-Wsign-conversion"
#endif
#endif

#include "iox2/iceoryx2.hpp"
#include "transmission_data.hpp"

#include <iostream>
#include <utility>

constexpr iox2::bb::Duration CYCLE_TIME = iox2::bb::Duration::from_secs(1);

auto main() -> int {
    using namespace iox2;
    set_log_level_from_env_or(LogLevel::Info);
    auto node = NodeBuilder().create<ServiceType::Ipc>().value();

    auto service = node.service_builder(ServiceName::create("My/Funk/ServiceName").value())
                       .publish_subscribe<TransmissionData>()
                       .open_or_create()
                       .value();

    auto publisher = service.publisher_builder().create().value();

    auto counter = 0;
    while (node.wait(CYCLE_TIME).has_value()) {
        counter += 1;

        auto sample = publisher.loan_uninit().value();

        auto initialized_sample =
            sample.write_payload(TransmissionData { counter, counter * 3, counter * 812.12 }); // NOLINT

        send(std::move(initialized_sample)).has_value();

        std::cout << "Send sample " << counter << "..." << std::endl;
    }

    std::cout << "exit" << std::endl;

    return 0;
}

#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
