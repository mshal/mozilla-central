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
        defines = sandbox['DEFINES']
        defines.extend(sandbox['ACDEFINES'])
        input_path = '../webidl/%s' % pp
        sandbox.generate_pp_rule(input_path, defines, [], '.')

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

    generated_events = sandbox['generated_events_webidl_files']
    generated_events_string = ' '.join(generated_events)

    python_string = '$(PYTHON_PATH) -Iparser -I$(MOZ_ROOT)/other-licenses/ply'
    globalgen_string = '%s GlobalGen.py Bindings.conf . %%f' % (python_string)
    bindinggen_string = 'echo all > changeddeps; echo %s > allfiles; echo %s > generatedevents; %s BindingGen.py --tup-support Bindings.conf . allfiles generatedevents changeddeps' % (all_webidl_files_string, generated_events_string, python_string)

    bindinggen_outputs = [f.replace('.webidl', 'Binding.h') for f in all_webidl_files]
    bindinggen_outputs.extend([f.replace('.webidl', 'Binding.cpp') for f in all_webidl_files])
    bindinggen_outputs.extend([f.replace('.webidl', '.h') for f in generated_events])
    bindinggen_outputs.extend([f.replace('.webidl', '.cpp') for f in generated_events])
    bindinggen_outputs.extend(['allfiles', 'generatedevents', 'changeddeps'])

    print ": %s |> ^o GlobalGen.py -> %%o^ %s |> %s | $(MOZ_ROOT)/<generated-headers>" % (all_webidl_files_string, globalgen_string, globalgen_targets_string)

    print ": %s | ParserResults.pkl |> ^o BindingGen.py [%i files]^ %s |> %s | $(MOZ_ROOT)/<generated-headers>" % (all_webidl_files_string, len(all_webidl_files), bindinggen_string, ' '.join(bindinggen_outputs))
