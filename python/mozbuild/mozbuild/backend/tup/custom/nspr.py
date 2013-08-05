#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    sandbox.objsgroup = "$(MOZ_ROOT)/nsprpub/<objs>"

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

    bld_file = None
    if sandbox.relativesrcdir in ('nsprpub/lib/ds', 'nsprpub/lib/libc/src'):
        bld_file = '_pl_bld.h'
    if sandbox.relativesrcdir == 'nsprpub/pr/src':
        bld_file = '_pr_bld.h'

    if bld_file:
        config_now = "%s/%s/nsprpub/config/now" % (sandbox.moz_root, sandbox.moz_objdir)

        suffix = sandbox.get_string('SUF')
        prod = "lib%s%s.%s" % (sandbox.get_string('LIBRARY_NAME'),
                               sandbox.get_string('LIBRARY_VERSION'),
                               sandbox.get_string('DLL_SUFFIX'))
        gen_bld = """shdate=`date "+%%Y-%%m-%%d %%T"`; """
        gen_bld += """shnow=`%s`; """ % (config_now)
        gen_bld += """(echo "#define _BUILD_STRING \\"$shdate\\""; """
        gen_bld += """if test ! -z "$shnow"; then echo "#define _BUILD_TIME ${shnow}%s"; fi; """ % (suffix)
        gen_bld += """echo "#define _PRODUCTION \\"%s\\"") > %%o""" % (prod)

        print ": $(MOZ_ROOT)/nsprpub/<progs> |> %s |> %s" % (gen_bld, bld_file)
        sandbox.extra_deps.append(bld_file)

    if sandbox.relativesrcdir == 'nsprpub/pr/src':
        # This directory is very bizarre - it includes md/unix/objs.mk, but
        # that defines CSRCS that aren't in the local directory. Somehow
        # it only expects to compile prvrsion.c in this directory, but link
        # all of the OBJS.
        sandbox.set_var('CSRCS', 'prvrsion.c')

        # ASFILES are already compiled in the required subdirectory.
        sandbox.set_var('ASFILES', [])
