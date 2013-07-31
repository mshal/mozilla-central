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

    if sandbox.relativesrcdir in ('nsprpub/lib/ds', 'nsprpub/lib/libc/src'):
        config_now = "%s/nsprpub/config/now" % (sandbox.moz_root)

        suffix = sandbox.get_string('SUF')
        prod = "lib%s%s.%s" % (sandbox.get_string('LIBRARY_NAME'),
                               sandbox.get_string('LIBRARY_VERSION'),
                               sandbox.get_string('DLL_SUFFIX'))
        gen_pl_bld = """shdate=`date "+%%Y-%%m-%%d %%T"`; """
        # TODO: Use config_now
        gen_pl_bld += """shnow=`%s`; """ % ('echo 12345')
#        gen_pl_bld += """shnow=`%s`; """ % (config_now)
        gen_pl_bld += """(echo "#define _BUILD_STRING \\"$shdate\\""; """
        gen_pl_bld += """if test ! -z "$shnow"; then echo "#define _BUILD_TIME ${shnow}%s"; fi; """ % (suffix)
        gen_pl_bld += """echo "#define _PRODUCTION \\"%s\\"") > %%o""" % (prod)

        # TODO: Use config_now
        print ": %s |> %s |> _pl_bld.h" % ("", gen_pl_bld)
        #print ": %s |> %s |> _pl_bld.h" % (config_now, gen_pl_bld)
        sandbox.extra_deps.append('_pl_bld.h')
