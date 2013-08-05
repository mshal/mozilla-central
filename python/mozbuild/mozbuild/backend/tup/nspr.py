#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    if 'include_subdir' in sandbox:
        include_subdir = sandbox.get_string('include_subdir') + '/'
    else:
        include_subdir = ""
    for header in sandbox['HEADERS']:
        print ": %s |> ^ INSTALL %%f^ cp %%f %%o |> $(DIST)/include/nspr/%s%%b | $(MOZ_ROOT)/<installed-headers>" % (header, include_subdir)

    for config in sandbox['CONFIGS']:
        print ": %s |> ^ INSTALL %%f^ cp %%f %%o |> $(DIST)/include/nspr/md/%%b | $(MOZ_ROOT)/<installed-headers>" % (config)

    if sandbox.relativesrcdir == 'nsprpub/pr/include/md':
        print ": %s |> ^ INSTALL %%f^ cp %%f %%o |> $(DIST)/include/nspr/prcpucfg.h | $(MOZ_ROOT)/<installed-headers>" % (sandbox.get_string('MDCPUCFG_H'))
