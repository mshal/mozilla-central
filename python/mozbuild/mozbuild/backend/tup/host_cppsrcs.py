#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

def generate_rules(sandbox):
    tupcpp = sandbox.get_tupcpp()

    host_cppsrcs = sandbox['HOST_CPPSRCS']
    tupcpp.generate_compile_rules(host_cppsrcs, 'C++ [host]', 'HOST_CXX',
                                  tupcpp.host_cpp_flags, host_prefix=True)
