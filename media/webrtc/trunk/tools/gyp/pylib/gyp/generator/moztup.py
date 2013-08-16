# Copyright (c) 2013 Mozilla Foundation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import gyp
import gyp.common
import sys
import os

generator_default_variables = {}
for dirname in ['INTERMEDIATE_DIR', 'SHARED_INTERMEDIATE_DIR', 'PRODUCT_DIR',
                                'LIB_DIR', 'SHARED_LIB_DIR']:
    # Some gyp steps fail if these are empty(!).
    generator_default_variables[dirname] = 'dir'
for unused in ['RULE_INPUT_PATH', 'RULE_INPUT_ROOT', 'RULE_INPUT_NAME',
                             'RULE_INPUT_DIRNAME', 'RULE_INPUT_EXT',
                             'EXECUTABLE_PREFIX', 'EXECUTABLE_SUFFIX',
                             'STATIC_LIB_PREFIX', 'STATIC_LIB_SUFFIX',
                             'SHARED_LIB_PREFIX', 'SHARED_LIB_SUFFIX',
                             'LINKER_SUPPORTS_ICF']:
    generator_default_variables[unused] = ''

def GetFlavor(params):
    """Returns |params.flavor| if it's set, the system's default flavor else."""
    flavors = {
        'win32': 'win',
        'darwin': 'mac',
        'sunos5': 'solaris',
        'freebsd7': 'freebsd',
        'freebsd8': 'freebsd',
    }
    flavor = flavors.get(sys.platform, 'linux')
    return params.get('flavor', flavor)


def CalculateVariables(default_variables, params):
    generator_flags = params.get('generator_flags', {})
    default_variables['OS'] = generator_flags.get('os', GetFlavor(params))

def striplib(name):
    "Strip lib prefixes from library names."
    if name[:3] == 'lib':
        return name[3:]
    return name

CPLUSPLUS_EXTENSIONS = set([
    '.cc',
    '.cpp',
    '.cxx'
])
COMPILABLE_EXTENSIONS = set([
    '.c',
    '.s',
    '.S',
    '.m',
    '.mm'
])
COMPILABLE_EXTENSIONS.update(CPLUSPLUS_EXTENSIONS)

def swapslashes(p):
    "Swap backslashes for forward slashes in a path."
    return p.replace('\\', '/')

def Compilable(filename):
    return os.path.splitext(filename)[1] in COMPILABLE_EXTENSIONS

class GypSandbox(object):
    def __init__(self, config, moz_root, moz_objdir, outputdir):
        self.config = config
        # relativesrcdir isn't actually needed for us, but cpp.py expects
        # it to be defined.
        self.relativesrcdir = '.'
        self.objs = []
        self.extra_deps = []
        self.extra_includes = []
        self.variables = dict()
        self.moz_root = moz_root
        self.moz_objdir = moz_objdir
        self.outputdir = outputdir
        self.objsgroup = ""
        from tup import makefile_parser
        makefile_parser.parse(self, None)
        self.makefile.set_var('DIST', os.path.join(moz_root, moz_objdir, 'dist'))

    def vpath_resolve(self, filename):
        return filename

    def get_string(self, name):
        value = self[name]
        if type(value) == list:
            return ' '.join(value)
        return value

    def __getitem__(self, name):
        if self.makefile:
            value = self.makefile.get_var(name)
            if value is not None:
                return value
        if name in self.config.defines:
            return [self.config.defines[name]]
        if name in self.config.substs:
            return [self.config.substs[name]]

        return []

    def __contains__(self, name):
        if self.makefile and self.makefile.get_var(name) is not None:
            return True
        if name in self.config.defines:
            return True
        if name in self.config.substs:
            return True
        return False

class TupfileGenerator(object):
    def __init__(self, target_dicts, data, options, flavor, sandbox):
        self.target_dicts = target_dicts
        self.data = data
        self.options = options
        self.flavor = flavor
        self.sandbox = sandbox

    def ProcessTargets(self, needed_targets):
        """
        Put all targets in proper order so that dependencies get built before
        the targets that need them.
        """
        for qualified_target in needed_targets:
            self.ProcessTarget(qualified_target)

    def ProcessTarget(self, qualified_target):
        """
        Generate tup rules for the target
        """
        spec = self.target_dicts[qualified_target]
        # Now write a Makefile for this target
        build_file, target, toolset = gyp.common.ParseQualifiedTarget(
            qualified_target)
        dir_target = os.path.dirname(build_file)
        rel_path = os.path.join(dir_target,
                                os.path.splitext(os.path.basename(build_file))[0] + '_' + target)

        self.WriteTargetRules(qualified_target, spec, dir_target, rel_path)

    def WriteTargetRules(self, qualified_target, spec, dirname, outdir):
        configs = spec['configurations']
        data = {}
        #TODO: handle actions/rules/copies
        if 'actions' in spec:
            pass
        if 'rules' in spec:
            pass
        if 'copies' in spec:
            pass
        libs = []
        if libs:
            data['EXTRA_LIBS'] = libs

        # Get DEFINES/INCLUDES
        for configname in sorted(configs.keys()):
            config = configs[configname]
            #XXX: this sucks
            defines = config.get('defines')
            if defines:
                data['DEFINES_%s' % configname] = ["-D%s" % d for d in defines]
            includes = []
            for i in config.get('include_dirs', []):
                # Make regular paths into srcdir-relative paths, leave
                # variable-specified paths alone.
                if i.startswith("$(") or os.path.isabs(i):
                    if ' ' in i:
                        includes.append('"%s"' % i)
                    else:
                        includes.append(i)
                else:
                    includes.append("$(srcdir)/" + i)
            if includes:
                data['INCLUDES_%s' % configname] = ["-I%s" %i for i in includes]
            #XXX: handle mac stuff?
# we want to use our compiler options in general
#            cflags = config.get('cflags')
#            if cflags:
#                data['CPPFLAGS_%s' % configname] = cflags
#            cflags_c = config.get('cflags_c')
#            if cflags_c:
#                data['CFLAGS_%s' % configname] = cflags_c
#            cflags_cc = config.get('cflags_cc')
#            if cflags_cc:
#                data['CXXFLAGS_%s' % configname] = cflags_cc
# we need to keep pkg-config flags however
            cflags_mozilla = config.get('cflags_mozilla')
            if cflags_mozilla:
                data['CPPFLAGS_%s' % configname] = cflags_mozilla
        sources = {
            'CPPSRCS': {'exts': CPLUSPLUS_EXTENSIONS, 'files': []},
            'CSRCS': {'exts': ['.c'], 'files': []},
            'CMSRCS': {'exts': ['.m'], 'files': []},
            'CMMSRCS': {'exts': ['.mm'], 'files': []},
            'ASFILES': {'exts': ['.s'], 'files': []},
            }
        copy_srcs = []
        for s in spec.get('sources', []):
            if not Compilable(s):
                continue

            # Special-case absolute paths, they'll get copied into the objdir
            # for compiling.
            if os.path.isabs(s):
                # GNU Make falls down pretty badly with spaces in filenames.
                # Conveniently, using a single-character ? as a wildcard
                # works fairly well.
                copy_srcs.append(s.replace(' ', '?'))
                s = os.path.basename(s)
                print >> sys.stderr, "tup error: Absolute path found in .gyp file: ", s
                sys.exit(1)

            ext = os.path.splitext(s)[1]
            for source_type, d in sources.iteritems():
                if ext in d['exts']:
                    d['files'].append(s)
                    break
            
        for source_type, d in sources.iteritems():
            if d['files']:
                data[source_type] = d['files']

        if copy_srcs:
            data['COPY_SRCS'] = copy_srcs

        if spec['type'] == 'executable':
            data['PROGRAM'] = spec['target_name']
        elif spec['type'] == 'static_library':
            data['LIBRARY_NAME'] = striplib(spec['target_name'])
            data['FORCE_STATIC_LIB'] = 1
        elif spec['type'] in ('loadable_module', 'shared_library'):
            data['LIBRARY_NAME'] = striplib(spec['target_name'])
            data['FORCE_SHARED_LIB'] = 1
        else:
            # Maybe nothing?
            return False
        self.WriteTupRules(data, dirname, outdir)
        return True

    def GetFlag(self, data, flag):
        return list(data[flag]) if flag in data else []

    def WriteTupRules(self, data, dirname, outdir):
        if self.sandbox['MOZ_DEBUG']:
            suffix = "Debug"
        else:
            suffix = "Release"

        includes = self.GetFlag(data, 'INCLUDES_' + suffix)

        cflags = self.GetFlag(data, 'DEFINES_' + suffix)
        cflags.extend(self.GetFlag(data, 'CPP_FLAGS_' + suffix))
        cflags.extend(self.GetFlag(data, 'CFLAGS_' + suffix))

        cxxflags = self.GetFlag(data, 'DEFINES_' + suffix)
        cxxflags.extend(self.GetFlag(data, 'CPP_FLAGS_' + suffix))
        cxxflags.extend(self.GetFlag(data, 'CXXFLAGS_' + suffix))

        cflag_string = ' '.join(cflags)
        cxxflag_string = ' '.join(cxxflags)

        if not dirname:
            dirname = '.'

        for inc in includes:
            inc = inc.replace('$(srcdir)', dirname)
            inc = inc.replace('$(DEPTH)', os.path.join(self.sandbox.moz_root, self.sandbox.moz_objdir))
            inc = inc.replace('$(DIST)', os.path.join(self.sandbox.moz_root, self.sandbox.moz_objdir, 'dist'))
            cflag_string += ' ' + inc
            cxxflag_string += ' ' + inc

        cppsrcs = []
        if 'CPPSRCS' in data:
            for src in data['CPPSRCS']:
                cppsrcs.append(os.path.join(dirname, src))

        csrcs = []
        if 'CSRCS' in data:
            for src in data['CSRCS']:
                csrcs.append(os.path.join(dirname, src))

        from tup import cpp
        tupcpp = cpp.TupCpp(self.sandbox, extra_flags=cxxflag_string)
        oldoutputdir = self.sandbox.outputdir
        self.sandbox.outputdir += '/%s' % (outdir)
        if cppsrcs:
            tupcpp.generate_compile_rules(cppsrcs, 'C++', 'CXX', tupcpp.cpp_flags)
        if csrcs:
            tupcpp.generate_compile_rules(csrcs, 'CC', 'CC', tupcpp.c_flags)

        if 'FORCE_STATIC_LIB' in data:
            from tup import linker
            objs = ['%s/%s' % (self.sandbox.outputdir, o) for o in self.sandbox.objs]
            linker.generate_desc_file(self.sandbox, objs,
                                      static_library_name=data['LIBRARY_NAME'])
        self.sandbox.objs = []
        self.sandbox.outputdir = oldoutputdir

def GenerateOutput(target_list, target_dicts, data, params):
    options = params['options']
    flavor = GetFlavor(params)
    generator_flags = params.get('generator_flags', {})
    moz_root = generator_flags['MOZ_ROOT']
    moz_objdir = generator_flags['MOZ_OBJDIR']
    outputdir = generator_flags['OUTPUTDIR']

    # Find the list of targets that derive from the gyp file(s) being built.
    needed_targets = set()
    build_files = set()
    for build_file in params['build_files']:
        build_file = os.path.normpath(build_file)
        for target in gyp.common.AllTargets(target_list, target_dicts, build_file):
            needed_targets.add(target)
            build_file_, _, _ = gyp.common.ParseQualifiedTarget(target)

    from mozbuild.backend.configenvironment import ConfigEnvironment
    config_status = os.path.join(moz_root, moz_objdir, 'config.status')
    env = ConfigEnvironment.from_config_status(config_status)

    sandbox = GypSandbox(env, moz_root, moz_objdir, outputdir)

    generator = TupfileGenerator(target_dicts, data, options, flavor, sandbox)
    generator.ProcessTargets(needed_targets)
