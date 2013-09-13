#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    tupcpp = sandbox.get_tupcpp()

    library_name = sandbox.get_string('HOST_LIBRARY_NAME')
    host_library = '%s/%s%s.%s' % (sandbox.outputdir,
                                   sandbox.get_string('LIB_PREFIX'),
                                   library_name,
                                   sandbox.get_string('LIB_SUFFIX'))

    inputs = ['%s/%s' % (sandbox.outputdir, o) for o in sandbox.hostobjs]
    input_string = ' '.join(inputs)

    host_ar = sandbox.get_string('HOST_AR')
    sandbox.makefile.set_var('@', host_library)
    host_ar_flags = sandbox.get_string('HOST_AR_FLAGS')
    host_ranlib = sandbox.get_string('HOST_RANLIB')

    library_group = '$(MOZ_ROOT)/<-l%s>' % (library_name)

    print ": %s |> ^ HOST_AR %%o^ %s %s %%f && %s %%o |> %s | %s" % (input_string, host_ar, host_ar_flags, host_ranlib, host_library, library_group)
    print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/host/lib/%%b | %s" % (host_library, library_group)
