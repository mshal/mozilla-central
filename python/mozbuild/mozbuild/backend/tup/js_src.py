#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    from tup import cpp
    tupcpp = cpp.TupCpp(sandbox, host_srcs_flag=True, js_src=True)
    tupcpp.generate_cpp_rules()

    print ": host_jsoplengen |> ./%f %o |> jsautooplen.h | $(MOZ_ROOT)/<generated-headers>"
    print ": host_jskwgen |> ./%f %o |> jsautokw.h | $(MOZ_ROOT)/<generated-headers>"
    print ": |> ^ embedjs.py -> %%o^ $(PYTHON) builtin/embedjs.py %s -p '%s' -m js.msg -o %%o %s |> selfhosted.out.h | selfhosted.js $(MOZ_ROOT)/<generated-headers>" % (sandbox.get_string('SELFHOSTED_DEFINES'), sandbox.get_string('CPP'), sandbox.get_string('selfhosting_srcs'))
