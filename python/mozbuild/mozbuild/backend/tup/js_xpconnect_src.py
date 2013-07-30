#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    flags = sandbox['DEFINES']
    flags.extend(sandbox['ACDEFINES'])
    print ": event_impl_gen.conf.in |> ^ Preprocessor %%f -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %%f > %%o |> event_impl_gen.conf" % (' '.join(flags))

    dictionary_gen = '$(PYTHON_PATH)'
    dictionary_gen += ' -I$(MOZ_ROOT)/other-licenses/ply'
    dictionary_gen += ' -I$(MOZ_ROOT)/python/codegen'
    dictionary_gen += ' -I$(MOZ_ROOT)/xpcom/idl-parser'
    dictionary_gen += ' dictionary_helper_gen.py -I$(DIST)/idl'
    dictionary_gen += ' --header-output DictionaryHelpers.h'
    dictionary_gen += ' --stub-output DictionaryHelpers.cpp'
    dictionary_gen += ' --cachedir=$(DIST)/idl'
    dictionary_gen += ' dictionary_helper_gen.conf'
    dictionary_gen += ' event_impl_gen.conf'
    print ": event_impl_gen.conf | $(MOZ_ROOT)/<installed-idls> |> ^ dictionary_helper_gen.py -> %%o^ %s |> DictionaryHelpers.h DictionaryHelpers.cpp" % (dictionary_gen)

    event_impl_gen = '$(PYTHON_PATH)'
    event_impl_gen += ' -I$(MOZ_ROOT)/other-licenses/ply'
    event_impl_gen += ' -I$(MOZ_ROOT)/python/codegen'
    event_impl_gen += ' -I$(MOZ_ROOT)/xpcom/idl-parser'
    event_impl_gen += ' event_impl_gen.py'
    event_impl_gen += ' -I$(DIST)/idl'
    event_impl_gen += ' --cachedir=$(DIST)/idl'
    event_impl_gen += ' --header-output GeneratedEvents.h'
    print ": event_impl_gen.conf | $(MOZ_ROOT)/<installed-idls> |> ^ event_impl_gen.py -> %%o^ %s %%f |> GeneratedEvents.h | $(MOZ_ROOT)/<generated-headers>" % (event_impl_gen)

    quickstubs_gen = '$(PYTHON_PATH)'
    quickstubs_gen += ' -I$(MOZ_ROOT)/other-licenses/ply'
    quickstubs_gen += ' -I$(MOZ_ROOT)/python/codegen'
    quickstubs_gen += ' -I$(MOZ_ROOT)/xpcom/idl-parser'
    quickstubs_gen += ' qsgen.py'
    quickstubs_gen += ' --idlpath=$(DIST)/idl'
    quickstubs_gen += ' --header-output dom_quickstubs.h'
    quickstubs_gen += ' --stub-output dom_quickstubs.cpp'
    quickstubs_gen += ' --cachedir=$(DIST)/idl'
    quickstubs_gen += ' dom_quickstubs.qsconf'
    print ": $(MOZ_ROOT)/<installed-idls> |> ^ qsgen.py -> %%o^ %s |> dom_quickstubs.h dom_quickstubs.cpp | $(MOZ_ROOT)/<generated-headers>" % (quickstubs_gen)

    generated_events_gen = '$(PYTHON_PATH)'
    generated_events_gen += ' -I$(MOZ_ROOT)/xpcom/idl-parser'
    generated_events_gen += ' -I$(MOZ_ROOT)/other-licenses/ply'
    generated_events_gen += ' -I$(MOZ_ROOT)/python/codegen'
    generated_events_gen += ' event_impl_gen.py'
    generated_events_gen += ' -I$(DIST)/idl'
    generated_events_gen += ' --class-declarations GeneratedEventClasses.h'
    generated_events_gen += ' --stub-output GeneratedEvents.cpp'
    generated_events_gen += ' event_impl_gen.conf'
    print ": event_impl_gen.conf $(MOZ_ROOT)/<installed-idls> |> ^ event_impl_gen.py -> %%o^ %s |> GeneratedEventClasses.h GeneratedEvents.cpp" % (generated_events_gen)
    for header in sandbox['_EXTRA_EXPORT_FILES']:
        print ": %s |> ^ INSTALL %%f^ cp %%f %%o |> $(DIST)/include/%%b | $(MOZ_ROOT)/<installed-headers>" % (header)
