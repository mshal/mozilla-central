# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

__all__ = [ 'gencxx', 'genipdl', 'parse', 'typecheck', 'writeifmodified' ]

import os, sys
from cStringIO import StringIO

from ipdl.cgen import IPDLCodeGen
from ipdl.lower import LowerToCxx
from ipdl.parser import Parser
from ipdl.type import TypeCheck

from ipdl.cxx.cgen import CxxCodeGen


def parse(specstring, filename='/stdin', includedirs=[ ], errout=sys.stderr, regen=False):
    '''Return an IPDL AST if parsing was successful.  Print errors to |errout|
    if it is not.'''
    # The file type and name are later enforced by the type checker.
    # This is just a hint to the parser.
    prefix, ext = os.path.splitext(filename)
    name = os.path.basename(prefix)
    if ext == '.ipdlh':
        type = 'header'
    else:
        type = 'protocol'
    return Parser(type, name).parse(specstring, os.path.abspath(filename), includedirs, errout, regen)


def typecheck(ast, errout=sys.stderr):
    '''Return True iff |ast| is well typed.  Print errors to |errout| if
    it is not.'''
    return TypeCheck().check(ast, errout)


def gencxx(ipdlfilename, ast, outheadersdir, outcppdir, tup_support=False):
    headers, cpps = LowerToCxx().lower(ast)

    def resolveHeader(hdr):
        if tup_support:
            return [ hdr, os.path.join(outheadersdir, hdr.name) ]
        else:
            return [
                hdr,
                os.path.join(
                    outheadersdir,
                    *([ns.name for ns in ast.namespaces] + [hdr.name]))
            ]
    def resolveCpp(cpp):
        return [ cpp, os.path.join(outcppdir, cpp.name) ]

    for ast, filename in ([ resolveHeader(hdr) for hdr in headers ]
                          + [ resolveCpp(cpp) for cpp in cpps ]):
        tempfile = StringIO()
        CxxCodeGen(tempfile).cgen(ast)
        if tup_support:
            write_tup(tempfile.getvalue(), filename)
        else:
            writeifmodified(tempfile.getvalue(), filename)


def genipdl(ast, outdir):
    return IPDLCodeGen().cgen(ast)


def writeifmodified(contents, file):
    dir = os.path.dirname(file)
    os.path.exists(dir) or os.makedirs(dir)

    oldcontents = None
    if os.path.exists(file):
        fd = open(file, 'rb')
        oldcontents = fd.read()
        fd.close()
    if oldcontents != contents:
        fd = open(file, 'wb')
        fd.write(contents)
        fd.close()

def write_tup(contents, file):
    fd = open(file, 'wb')
    fd.write(contents)
    fd.close()
