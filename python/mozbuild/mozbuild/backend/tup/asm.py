#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

def generate_rules(sandbox):
    asfiles = sandbox['ASFILES']
    asm_compiler = sandbox.get_string('AS')
    asflags = sandbox.get_string('ASFLAGS')
    as_dash_c_flag = sandbox.get_string('AS_DASH_C_FLAG')
    obj_suffix = sandbox.get_string('OBJ_SUFFIX')
    vpath = sandbox['VPATH']
    if asm_compiler.startswith('ml'):
        asoutoption = '-Fo'
    else:
        asoutoption = '-o '

#    if self.extra_deps:
#        extra_deps_string = " | " + (' '.join(self.extra_deps))
#    else:
#        extra_deps_string = ""
    extra_deps_string = ""

    for filename in asfiles:
        fullpath = sandbox.vpath_resolve(filename)
        print ": %s %s |> ^ ASM %%f^ %s %s%%o %s %s %%f |> %s/%%B.%s" % (fullpath, extra_deps_string, asm_compiler, asoutoption, asflags, as_dash_c_flag, sandbox.outputdir, obj_suffix)
        basename, ext = os.path.splitext(os.path.basename(fullpath))
        sandbox.objs.append("%s.%s" % (basename, obj_suffix))
