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
tupmk = tup_makefile.TupMakefile(moz_root, moz_objdir, allow_includes=True)

tupmk.parse('.')

all_webidl_files = tupmk.get_var('all_webidl_files')
all_webidl_files_string = ' '.join(all_webidl_files)
globalgen_targets_string = ' '.join(tupmk.get_var('globalgen_targets'))
globalgen_targets_string += ' ParserResults.pkl parser.out WebIDLGrammar.pkl'
globalgen_targets_string += ' | $(MOZ_ROOT)/dist/include/<installed-headers>'

python_string = '$(PYTHON) $(PYTHONPATH) -Iparser'
globalgen_string = '%s GlobalGen.py Bindings.conf . %%f' % (python_string)
bindinggen_header_string = '^ BindingGen.py -> %%o^ %s BindingGen.py header Bindings.conf %%BBinding %%f' % (python_string)
bindinggen_cpp_string = '^ BindingGen.py -> %%o^ %s BindingGen.py cpp Bindings.conf %%BBinding %%f' % (python_string)

print ": %s |> ^ GlobalGen.py -> %%o^ %s |> %s" % (all_webidl_files_string, globalgen_string, globalgen_targets_string)

for idl in all_webidl_files:
    print ": %s | ParserResults.pkl |> %s |> %%BBinding.h | $(MOZ_ROOT)/dist/include/<installed-headers>" % (idl, bindinggen_header_string)
    print ": %s | ParserResults.pkl |> %s |> %%BBinding.cpp" % (idl, bindinggen_cpp_string)

cpp = tup_cpp.TupCpp(tupmk, moz_objdir, target_srcs_flag=True)
cpp.generate_cpp_rules()

# With the make build, the Test webidl files are converted to *Binding.cpp files
# in the dom/bindings/ directory, but are not compiled until make recurses into
# dom/bindings/test, which then recurses back to dom/bindings/ for each cpp file
# to get it compiled. Here, we'll just compile them all from dom/bindings/, so
# add any test files to CPPSRCS.
test_idls = tupmk.get_var('test_webidl_files')
if test_idls:
    for example in ['TestExampleInterface', 'TestExampleProxyInterface']:
        outputs = '%s-example.cpp %s-example.h' % (example, example)
        outputs += ' | $(MOZ_ROOT)/dist/include/<installed-headers>'
        print ": | ParserResults.pkl |> %s ExampleGen.py Bindings.conf %s |> %s" % (python_string, example, outputs)

    testsrcs = []
    for idl in test_idls:
        base, extension = os.path.splitext(idl)
        testsrcs.append("%sBinding.cpp" % (base))

    cpp.extra_includes = ['test']
    cpp.generate_cpp_rules(testsrcs)
