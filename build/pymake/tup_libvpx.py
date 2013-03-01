#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import tup_makefile
import tup_cpp

if len(sys.argv) < 3:
    sys.exit('usage: %s MOZ_ROOT MOZ_OBJDIR' % sys.argv[0])

moz_root = sys.argv[1]
moz_objdir = sys.argv[2]
tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True,
                                 need_config_mk=True)

tupmk.parse('.')
cpp = tup_cpp.TupCpp(tupmk, moz_objdir, target_srcs_flag=True)

# The libvpx Makefile creates an asm file (asm_enc_offsets.s) from
# asm_enc_offsets.c, and then we conver that to asm_enc_offsets.asm, which is
# included by other .asm files in the directory.
vpath = tupmk.get_var('VPATH')
if tupmk.get_var('MOZ_VP8_ENCODER'):
    cpp.generate_compile_rules(['asm_enc_offsets.c'], 'CC -S', '$(CC)', vpath, cpp.c_flags, compile_flag='-S', obj_suffix='s')
    offset_pattern = tupmk.get_var_string('OFFSET_PATTERN')
    vpx_as_conversion = tupmk.get_var('VPX_AS_CONVERSION')
    if vpx_as_conversion:
        vpx_as_conversion_string = '| %s' % (vpx_as_conversion[0])
    else:
        vpx_as_conversion_string = ""
    print ": asm_enc_offsets.s |> grep %s %%f | sed -e 's/[$$\#]//g' %s > %%o |> %%B.asm" % (offset_pattern, vpx_as_conversion_string)

cpp.extra_deps = ['asm_enc_offsets.asm']
cpp.generate_cpp_rules()
