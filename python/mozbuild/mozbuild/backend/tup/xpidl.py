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
            print ": foreach %s |> !cp |> $(DIST)/idl/%%b | $(MOZ_ROOT)/<installed-idls>" % (xpidl)

            # Generate the .h file locally. Put it in the {xpidl} bin for
            # each file so we don't have to duplicate path manipulations
            # here.
            print ": foreach %s | $(MOZ_ROOT)/<installed-idls> |> ^ python header.py [%%f -> %%o]^ $(PYTHON_PATH) $(PLY_INCLUDE) $(MOZ_ROOT)/xpcom/idl-parser/header.py %s %%f -o %%o --cachedir=$(MOZ_ROOT)/xpcom/idl-parser |> %s/%%B.h | $(MOZ_ROOT)/<installed-headers> {%s}" % (xpidl, flags, sandbox.outputdir, xpidl)

            # Install the .h file to dist/include
            print ": foreach {%s} |> !cp |> $(DIST)/include/%%b | $(MOZ_ROOT)/<installed-headers>" % (xpidl)

            # Generate the .xpt file
            print ": foreach %s | $(MOZ_ROOT)/<installed-idls> |> ^ typelib.py %%o^ $(PYTHON_PATH) $(PLY_INCLUDE) -I$(MOZ_ROOT)/xpcom/typelib/xpt/tools $(MOZ_ROOT)/xpcom/idl-parser/typelib.py %s %%f --cachedir=$(MOZ_ROOT)/xpcom/idl-parser -o %%o |> %s/%%B.xpt {xpts}" % (xpidl, flags, sandbox.outputdir)

        # Link the module xpt
        print ": {xpts} |> ^ xpt.py link %%o^ $(PYTHON) $(MOZ_ROOT)/xpcom/typelib/xpt/tools/xpt.py link %%o %%f |> %s/%s.xpt {module_xpt}" % (sandbox.outputdir, xpidl_module)

        # Export the module xpt
        print ": {module_xpt} |> !cp |> $(DIST)/bin/components/%b | $(MOZ_ROOT)/<installed-xpts>"
