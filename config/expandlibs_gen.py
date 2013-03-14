# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Given a list of object files and library names, prints a library
descriptor to standard output'''

from __future__ import with_statement
import sys
import os
import expandlibs_config as conf
from expandlibs import LibDescriptor, isObject, ensureParentDir, ExpandLibsDeps
from optparse import OptionParser

def generate(args, path_base):
    desc = LibDescriptor()
    for arg in args:
        if isObject(arg):
            if os.path.exists(arg):
                if path_base:
                    path = os.path.normpath(os.path.join(path_base, arg))
                else:
                    path = os.path.abspath(arg)
                desc['OBJS'].append(path)
            else:
                raise Exception("File not found: %s" % arg)
        elif os.path.splitext(arg)[1] == conf.LIB_SUFFIX:
            if os.path.exists(arg) or os.path.exists(arg + conf.LIBS_DESC_SUFFIX):
                if path_base:
                    path = os.path.normpath(os.path.join(path_base, arg))
                else:
                    path = os.path.abspath(arg)
                desc['LIBS'].append(path)
            else:
                raise Exception("File not found: %s" % arg)
    return desc

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--depend", dest="depend", metavar="FILE",
        help="generate dependencies for the given execution and store it in the given file")
    parser.add_option("-o", dest="output", metavar="FILE",
        help="send output to the given file")
    parser.add_option("--relative-path", dest="relative_path",
        default="", type=str,
        help="use paths relative to the repository root instead of full paths")

    (options, args) = parser.parse_args()
    if not options.output:
        raise Exception("Missing option: -o")

    if options.relative_path:
        # For a relative_path like "../..", we want the last two parts of the
        # CWD, so count the slashes and add 1 to get the number of path parts
        # that we want.
        cwd = os.getcwd()
        cwd_parts = cwd.split('/')
        path_count = options.relative_path.count('/') + 1
        path_base = os.path.join(*cwd_parts[-path_count:])
    else:
        path_base = ""

    ensureParentDir(options.output)
    with open(options.output, 'w') as outfile:
        print >>outfile, generate(args, path_base)
    if options.depend:
        ensureParentDir(options.depend)
        with open(options.depend, 'w') as depfile:
            depfile.write("%s : %s\n" % (options.output, ' '.join(ExpandLibsDeps(args))))
