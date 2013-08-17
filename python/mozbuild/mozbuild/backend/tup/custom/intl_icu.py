#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def generate_rules(sandbox):
    cppflags = sandbox.get_string('CPPFLAGS')
    defs = sandbox.get_string('DEFS')
    cxxflags = sandbox.get_string('CXXFLAGS')
    cflags = sandbox.get_string('CFLAGS')
    cc = sandbox.get_string('CC')
    cxx = sandbox.get_string('CXX')
    files = set(os.listdir('.'))
    for obj in sandbox['OBJECTS']:
        root, ext = os.path.splitext(obj)
        cfile = '%s.c' % root
        if cfile in files:
            print ": foreach %s |> ^ %s %%f^ %s %s %s %s -c %%f -o %%o |> %s/%s {objs}" % (
                cfile, cc, cc, cppflags, defs, cflags, sandbox.outputdir, obj
            )
        else:
            cppfile = '%s.cpp' % root
            print ": foreach %s |> ^ %s %%f^ %s %s %s %s -c %%f -o %%o |> %s/%s {objs}" % (
                cppfile, cxx, cxx, cppflags, defs, cxxflags, sandbox.outputdir, obj
            )
    ar = sandbox.get_string('AR')
    arflags = sandbox.get_string('ARFLAGS')
    arout = sandbox.get_string('AR_OUTOPT')
    target = sandbox.get_string('TARGET')
    target_stubname = sandbox.get_string('TARGET_STUBNAME')
    lib_group = '$(MOZ_ROOT)/<-licu%s>' % (target_stubname)
    print ": {objs} |> ^ AR %%o^ %s %s %s%%o %%f |> %s/%s %s" % (
        ar, arflags, arout, sandbox.outputdir, target, lib_group
    )
    print ": %s/%s |> ^ INSTALL %%o^ cp %%f %%o |> $(MOZ_ROOT)/@(MOZ_OBJDIR)/js/src/intl/icu/lib/%s %s" % (
        sandbox.outputdir, target, target, lib_group
    )
