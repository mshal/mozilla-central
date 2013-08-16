#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    print ": |> ^ Preprocess -> CSS2Properties.webidl^ %s -I$(MOZ_ROOT)/layout/style ../webidl/CSS2PropertiesProps.h | $(PYTHON) GenerateCSS2PropertiesWebIDL.py ../webidl/CSS2Properties.webidl.in > %%o |> CSS2Properties.webidl" % (sandbox.get_string('CPP'))

    pp_webidl = sandbox['preprocessed_webidl_files']
    for pp in pp_webidl:
        import distinstall
        defines = sandbox['DEFINES']
        defines.extend(sandbox['ACDEFINES'])
        input_path = '../webidl/%s' % pp
        distinstall.generate_pp_rule(sandbox, input_path, defines, [], '.')

    webidl = sandbox['webidl_files']
    for idl in webidl:
        print ": ../webidl/%s |> !cp |> %%b" % (idl)

    test_webidl = sandbox['test_webidl_files']
    for idl in test_webidl:
        print ": test/%s |> !cp |> %%b" % (idl)

    all_webidl_files = sandbox['all_webidl_files']
    all_webidl_files_string = ' '.join(all_webidl_files)
    globalgen_targets_string = ' '.join(sandbox['globalgen_targets'])
    globalgen_targets_string += ' ParserResults.pkl parser.out WebIDLGrammar.pkl'
    globalgen_targets_string += ' | $(MOZ_ROOT)/<generated-headers>'

    python_string = '$(PYTHON_PATH) -Iparser -I$(MOZ_ROOT)/other-licenses/ply'
    globalgen_string = '%s GlobalGen.py Bindings.conf . %%f' % (python_string)
    bindinggen_string = 'echo all > changeddeps; echo %s > allfiles; %s BindingGen.py --tup-support Bindings.conf . allfiles changeddeps' % (all_webidl_files_string, python_string)

    bindinggen_outputs = ['%sBinding.h' % (f.replace('.webidl', '')) for f in all_webidl_files]
    bindinggen_outputs.extend(['%sBinding.cpp' % (f.replace('.webidl', '')) for f in all_webidl_files])
    bindinggen_outputs.extend(['allfiles', 'changeddeps'])

    print ": %s |> ^o GlobalGen.py -> %%o^ %s |> %s" % (all_webidl_files_string, globalgen_string, globalgen_targets_string)

    print ": %s | ParserResults.pkl |> ^o BindingGen.py [%i files]^ %s |> %s" % (all_webidl_files_string, len(all_webidl_files), bindinggen_string, ' '.join(bindinggen_outputs))
