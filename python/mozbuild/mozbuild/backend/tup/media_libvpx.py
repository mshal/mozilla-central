#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    if sandbox['MOZ_VP8_ENCODER']:
        from cpp import TupCpp
        tupcpp = TupCpp(sandbox)
        tupcpp.generate_compile_rules(['asm_enc_offsets.c'], 'CC -S', 'CC', tupcpp.c_flags, compile_flag='-S', obj_suffix='s')
        offset_pattern = sandbox.get_string('OFFSET_PATTERN')
        vpx_as_conversion = sandbox['VPX_AS_CONVERSION']
        if vpx_as_conversion:
            vpx_as_conversion_string = '| %s' % (vpx_as_conversion[0])
        else:
            vpx_as_conversion_string = ""
        print ": %s/asm_enc_offsets.s |> grep %s %%f | sed -e 's/[$$\#]//g' %s > %%o |> %%B.asm" % (sandbox.outputdir, offset_pattern, vpx_as_conversion_string)
        sandbox.extra_deps.append('asm_enc_offsets.asm')
