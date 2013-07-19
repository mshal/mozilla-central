#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

def generate_rules(sandbox):
    xpidlsrcs = sandbox['XPIDL_SOURCES']
    if xpidlsrcs:
        xpidl_module = sandbox['XPIDL_MODULE']
        if not xpidl_module:
            xpidl_module = sandbox['MODULE']
            if not xpidl_module:
                return
        flags = sandbox.get_string('XPIDL_FLAGS')
        for xpidl in xpidlsrcs:
            # Install the .idl file in dist/idl/
            print ": foreach %s |> !cp |> $(MOZ_ROOT)/dist/idl/%%b | $(MOZ_ROOT)/<installed-idls>" % (xpidl)

            # Generate the .h file locally. Put it in the {xpidl} bin for
            # each file so we don't have to duplicate path manipulations
            # here.
            print ": foreach %s | $(MOZ_ROOT)/<installed-idls> |> ^ python header.py [%%f -> %%o]^ $(PYTHON_PATH) $(PLY_INCLUDE) $(MOZ_ROOT)/xpcom/idl-parser/header.py -I$(MOZ_ROOT)/dist/idl %%f -o %%o --cachedir=$(MOZ_ROOT)/xpcom/idl-parser |> %%B.h | $(MOZ_ROOT)/dist/include/<installed-headers> {%s}" % (xpidl, xpidl)

            # Install the .h file to dist/include
            print ": foreach {%s} |> !cp |> $(MOZ_ROOT)/dist/include/%%b | $(MOZ_ROOT)/dist/include/<installed-headers>" % (xpidl)

            # Generate the .xpt file
            print ": foreach %s | $(MOZ_ROOT)/<installed-idls> |> ^ typelib.py %%o^ $(PYTHON_PATH) $(PLY_INCLUDE) -I$(MOZ_ROOT)/xpcom/typelib/xpt/tools $(MOZ_ROOT)/xpcom/idl-parser/typelib.py -I$(MOZ_ROOT)/dist/idl %s %%f --cachedir=$(MOZ_ROOT)/xpcom/idl-parser -o %%o |> %%B.xpt {xpts}" % (xpidl, flags)

        # Link the module xpt
        print ": {xpts} |> ^ xpt.py link %%o^ $(PYTHON) $(MOZ_ROOT)/xpcom/typelib/xpt/tools/xpt.py link %%o %%f |> %s.xpt {module_xpt}" % (xpidl_module)

        # Export the module xpt
        print ": {module_xpt} |> !cp |> $(MOZ_ROOT)/dist/bin/components/%b | $(MOZ_ROOT)/dist/bin/components/<installed-xpts>"
