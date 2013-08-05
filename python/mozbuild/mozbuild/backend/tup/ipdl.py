#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os

if len(sys.argv) < 3:
    sys.exit('usage: %s MOZ_ROOT MOZ_OBJDIR' % sys.argv[0])

moz_root = sys.argv[1]
moz_objdir = sys.argv[2]

sys.path.append(os.path.join(os.getcwd(), moz_root, 'python', 'mozbuild'))
sys.path.append(os.path.join(os.getcwd(), moz_root, 'config'))
from mozbuild.backend.configenvironment import ConfigEnvironment
from mozbuild.frontend.reader import MozbuildSandbox

# TODO: This sucks, but we need to find the list of outputs before generating
# the monolithic ipdl.py rule.
ipdldirs = [
    'content/media/webspeech/synth',
    'dom/bluetooth',
    'dom/devicestorage',
    'dom/indexedDB/ipc',
    'dom/ipc',
    'dom/mobilemessage/src',
    'dom/network/src',
    'dom/plugins/ipc',
    'dom/src/storage',
    'gfx/layers',
    'hal',
    'ipc/glue',
    'ipc/ipdl/test/cxx',
    'ipc/testshell',
    'js/ipc',
    'layout/ipc',
    'netwerk/cookie',
    'netwerk/ipc',
    'netwerk/protocol/ftp',
    'netwerk/protocol/http',
    'netwerk/protocol/websocket',
    'netwerk/protocol/wyciwyg',
    'uriloader/exthandler',
    'uriloader/prefetch',
]

# TODO: The file_namespaces and dir_namespaces also suck - technically we need
# to parse the .ipdl/.ipdlh files just to see where the header files will be
# created, since they go into subdirectories based on the namespace declarations
# in the .ipdl files.
file_namespaces = {
    # This is the only file in dom/ipc that goes into mozilla/ipc, the rest go
    # into mozilla/dom
    'PDocumentRenderer': 'mozilla/ipc',

    # Some files from ipc/ipdl/test/cxx use unique namespaces
    'PTestDataStructuresCommon': 'mozilla/_foo',
    'PTestOpensOpened': 'mozilla/_ipdltest2',
}
dir_namespaces = {
    'content/media/webspeech/synth/ipc': 'mozilla/dom',
    'dom/bluetooth/ipc': 'mozilla/dom/bluetooth',
    'dom/devicestorage': 'mozilla/dom/devicestorage',
    'dom/indexedDB/ipc': 'mozilla/dom/indexedDB',
    'dom/ipc': 'mozilla/dom',
    'dom/mobilemessage/src/ipc': 'mozilla/dom/mobilemessage',
    'dom/network/src': 'mozilla/net',
    'dom/plugins/ipc': 'mozilla/plugins',
    'dom/src/storage': 'mozilla/dom',
    'gfx/layers/ipc': 'mozilla/layers',
    'hal/sandbox': 'mozilla/hal_sandbox',
    'ipc/glue': 'mozilla/ipc',
    'ipc/ipdl/test/cxx': 'mozilla/_ipdltest',
    'ipc/testshell': 'mozilla/ipc',
    'js/ipc': 'mozilla/jsipc',
    'layout/ipc': 'mozilla/layout',
    'netwerk/cookie': 'mozilla/net',
    'netwerk/ipc': 'mozilla/net',
    'netwerk/protocol/ftp': 'mozilla/net',
    'netwerk/protocol/http': 'mozilla/net',
    'netwerk/protocol/websocket': 'mozilla/net',
    'netwerk/protocol/wyciwyg': 'mozilla/net',
    'uriloader/exthandler': 'mozilla/dom',
    'uriloader/prefetch': 'mozilla/docshell',
}

cppsrcs = []
inputs = []
incdirs = []
outputs = ['_ipdlheaders/IPCMessageStart.h', 'ipdl_lextab.py', 'ipdl_yacctab.py']

config_status = os.path.join(moz_root, moz_objdir, 'config.status')
env = ConfigEnvironment.from_config_status(config_status)

for ipdldir in ipdldirs:
    subdir = os.path.join(moz_root, ipdldir)
    mozbuild_dir = os.path.join(os.getcwd(), subdir)
    root_path = os.path.normpath(os.path.join(os.getcwd(), moz_root))

    # Make sure include('/fo') is in the tup directory, rather than the
    # root fs until tup is fixed
    env.topsrcdir = root_path

    mozbuild_file = os.path.join(os.getcwd(), subdir, 'moz.build')
    sandbox = MozbuildSandbox(env, mozbuild_file)
    if sandbox.mozbuild_enabled(os.path.normpath(mozbuild_dir), root_path):
        sandbox.exec_file(mozbuild_file, filesystem_absolute=True)
        for ipdl in sandbox['IPDL_SOURCES']:
            inputs.append(os.path.join(subdir, ipdl))
            (filepath, ext) = os.path.splitext(ipdl)
            (dirname, basename) = os.path.split(filepath)
            incdirs.append('-I%s/%s' % (subdir, dirname))
            basename = os.path.basename(basename)
            extensions = ['']
            if ext == '.ipdl':
                extensions.extend(['Child', 'Parent'])

            if basename in file_namespaces:
                headerdir = file_namespaces[basename]
            else:
                if dirname:
                    dirkey = "%s/%s" % (ipdldir, dirname)
                else:
                    dirkey = ipdldir
                headerdir = dir_namespaces[dirkey]

            for extension in extensions:
                cppsrc = "%s%s.cpp" % (basename, extension)
                cppsrcs.append(cppsrc)
                outputs.append(cppsrc)
                outputs.append("_ipdlheaders/%s/%s%s.h" % (headerdir, basename, extension))

# Create a single rule to process all of the .ipdl/.ipdlh files in one go.
# Although we could theoretically process these individually, the inter-.ipdl
# dependencies are such that all .ipdl files are dependent on all others.
print ": ",
print ' '.join(inputs),
print "|> ^ tup-ipdl.py %f^ $(PYTHON_PATH) -I$(MOZ_ROOT)/other-licenses/ply ipdl.py --outheaders-dir=_ipdlheaders ",
print ' '.join(incdirs),
print "%f |>",
print ' '.join(outputs),
print ' | $(MOZ_ROOT)/<installed-headers>'

sys.path.append(os.path.join(os.getcwd(), moz_root, 'build', 'pymake'))
from mozbuildmakesandbox import MozbuildMakeSandbox
import makefile_parser
sandbox = MozbuildMakeSandbox(env, mozbuild_file, moz_root, moz_objdir, [], 'ipc/ipdl')

makefile_parser.parse(sandbox, 'Makefile.in')
tupcpp = sandbox.get_tupcpp()
tupcpp.generate_compile_rules(cppsrcs, 'C++', 'CXX', tupcpp.cpp_flags)
#tupcpp.generate_desc_file()
