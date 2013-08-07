#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def resolve_libraries(sandbox, libs):
    flags = []
    deps = []
    for lib in libs:
        if lib.startswith('ctypes/libffi/.libs'):
            lib = lib.replace('ctypes/libffi/.libs', 'ctypes/libffi')

        if lib.startswith('-l'):
            deps.append('$(MOZ_ROOT)/<%s>' % lib)
            if lib == '-lxul':
                # TODO: Why doesn't this get picked up automatically from
                # group dependencies?
                deps.append('$(MOZ_ROOT)/<-lmozsqlite3>')
        if lib.endswith('.a'):
            if sandbox.moz_objdir not in lib:
                lib = '%s/%s' % (sandbox.outputdir, lib)
            libname = os.path.basename(lib)
            lib_prefix = sandbox.get_string('LIB_PREFIX')
            lib_suffix = sandbox.get_string('LIB_SUFFIX')
            if libname.startswith(lib_prefix) and libname.endswith(lib_suffix):
                libname = libname[len(lib_prefix):-len(lib_suffix)-1]
                deps.append('$(MOZ_ROOT)/<-l%s>' % (libname))

        flags.append(lib)
    return flags, deps

def generate_desc_file(sandbox, objs, static_library_name=None):
    lib_prefix = sandbox.get_string('LIB_PREFIX')
    lib_suffix = sandbox.get_string('LIB_SUFFIX')
    program = sandbox.get_string('PROGRAM')

    if program and objs:
        output = "%s/%s" % (sandbox.outputdir, program)
        program_exec = "$(PYTHON_PATH)"
        program_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config"
        program_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/_virtualenv/lib/python2.7/site-packages"
        program_exec += " $(MOZ_ROOT)/config/expandlibs_exec.py"
        program_exec += " --relative-path $(MOZ_ROOT)"
        program_exec += " --target %o"
        program_exec += " --"
        program_exec += ' ' + sandbox.get_string('CCC')
        program_exec += ' -o %s' % output
        program_exec += ' ' + sandbox.get_string('CXXFLAGS')
        progobjs = sandbox['PROGOBJS']
        if progobjs:
            progobjs = ['%s/%s' % (sandbox.outputdir, o) for o in progobjs]
        else:
            progobjs = objs
        inputs = ' '.join(progobjs)
        program_exec += ' ' + inputs

        flag_group = [
            'RESFILE',
            'WIN32_EXE_LDFLAGS',
            'LDFLAGS',
            'WRAP_LDFLAGS',
            'LIBS_DIR',
            'LIBS',
            'MOZ_GLUE_PROGRAM_LDFLAGS',
            'OS_LIBS',
            'EXTRA_LIBS',
            'BIN_FLAGS',
            'EXE_DEF_FILE',
        ]
        flags = sandbox.get_tupcpp().get_all_flags(flag_group, program)
        actual_libs, lib_deps = resolve_libraries(sandbox, flags)
        inputs += ' ' + ' '.join(lib_deps)
        program_exec += ' ' + ' '.join(actual_libs)

        print ": %s |> ^ LINK %%o^ %s |> %s" % (inputs, program_exec, output)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/bin/%%b" % (output)

    if sandbox['FORCE_SHARED_LIB']:
        library_name = '%s%s%s' % (sandbox.get_string('DLL_PREFIX'),
                                   sandbox.get_string('SHARED_LIBRARY_NAME'),
                                   sandbox.get_string('DLL_SUFFIX'))
        output = '%s/%s' % (sandbox.outputdir, library_name)
        sandbox.makefile.set_var('@', output)
        inputs = ' '.join(objs)

        # In make, EXTRA_DSO_LIBS is converted by the EXPAND_MOZLIBNAME
        # macro called from rules.mk. We expand it here before evaluating
        # EXTRA_DSO_LDOPTS, where it is used.
        extra_dso_libs = sandbox.get_string('EXTRA_DSO_LIBS')
        if extra_dso_libs:
            extra_dso_libs = '$(MOZ_ROOT)/dist/lib/%s%s.%s' % (lib_prefix,
                                                               extra_dso_libs,
                                                               lib_suffix)
            sandbox.makefile.set_var('EXTRA_DSO_LIBS', extra_dso_libs)

        expandlibs_exec = "$(PYTHON_PATH)"
        expandlibs_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config"
        expandlibs_exec += " -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/_virtualenv/lib/python2.7/site-packages"
        expandlibs_exec += " $(MOZ_ROOT)/config/expandlibs_exec.py"
        expandlibs_exec += " --relative-path $(MOZ_ROOT)"
        expandlibs_exec += " --target %o"
        expandlibs_exec += " " + sandbox.get_string('EXPAND_MKSHLIB_ARGS')
        expandlibs_exec += " --"
        expandlibs_exec += " " + sandbox.get_string('MKSHLIB')
        expandlibs_exec += " %f"

        # Some files we need (like symverscript) are in the generated-headers
        # group
        lib_deps = ['$(MOZ_ROOT)/<generated-headers>']
        lib_flags = []

        ld_flag_groups = [
            'LDFLAGS',
            'WRAP_LDFLAGS',
            'SHARED_LIBRARY_LIBS',
            'EXTRA_DSO_LDOPTS',
            'MOZ_GLUE_LDFLAGS',
            'OS_LIBS',
            'EXTRA_LIBS',
            'DEF_FILE',
            'SHLIB_LDENDFILE'
        ]
        ld_flags = sandbox.get_tupcpp().get_all_flags(ld_flag_groups, library_name)

        lib_flags, lib_deps = resolve_libraries(sandbox, ld_flags)

        # This logic is in rules.mk, but should probably be in config.mk
        if sandbox['IS_COMPONENT']:
            lib_flags.append(sandbox.get_string('MOZ_COMPONENTS_VERSION_SCRIPT_LDFLAGS'))
            # TODO: Linux only, others have different flags
            lib_flags.append('-Wl,-Bsymbolic')

        expandlibs_exec += " " + ' '.join(lib_flags)
        lib_deps_string = ' '.join(lib_deps)

        print ": %s | %s |> ^ SHLIB %%o^ %s |> %s" % (inputs, lib_deps_string, expandlibs_exec, output)
        output_group = '$(MOZ_ROOT)/<-l%s>' % (sandbox.get_string('SHARED_LIBRARY_NAME'))
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (output, output_group)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/bin/%%b | %s" % (output, output_group)

        if not sandbox['NO_DIST_INSTALL'] and sandbox['IS_COMPONENT']:
            dist_subdir = sandbox.get_string('DIST_SUBDIR')
            if dist_subdir:
                component_group = '$(MOZ_ROOT)/<components-%s>' % dist_subdir
            else:
                component_group = '$(MOZ_ROOT)/<components>'
            print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> %s/components/%%b | %s" % (output, sandbox.get_string('FINAL_TARGET'), component_group)
    else:
        if not static_library_name:
            static_library_name = sandbox.get_string('STATIC_LIBRARY_NAME')

        if static_library_name:
            output = '%s/%s%s.%s' % (sandbox.outputdir,
                                     sandbox.get_string('LIB_PREFIX'),
                                     static_library_name,
                                     sandbox.get_string('LIB_SUFFIX'))
            output_desc = '%s.%s' % (output,
                                     sandbox.get_string('LIBS_DESC_SUFFIX'))
            inputs = ' '.join(objs)
            cmd_inputs = inputs

            libs, deps = resolve_libraries(sandbox, sandbox['SHARED_LIBRARY_LIBS'])
            inputs += ' ' + ' '.join(deps)
            cmd_inputs += ' ' + ' '.join(libs)

            output_group = '$(MOZ_ROOT)/<-l%s>' % static_library_name
            print ": %s |> ^ expandlibs_gen.py %%o^ $(PYTHON_PATH) -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/_virtualenv/lib/python2.7/site-packages $(MOZ_ROOT)/config/expandlibs_gen.py -o %%o %s --relative-path $(MOZ_ROOT) |> %s | %s" % (inputs, cmd_inputs, output_desc, output_group)

            export_library = sandbox.get_string('EXPORT_LIBRARY')
            desc_dir = None
            if export_library:
                if export_library == '1':
                    if sandbox['IS_COMPONENT']:
                        desc_dir = '$(MOZ_ROOT)/@(MOZ_OBJDIR)/staticlib/components'
                    else:
                        desc_dir = '$(MOZ_ROOT)/@(MOZ_OBJDIR)/staticlib'
                else:
                    if sandbox.moz_objdir in export_library:
                        # At least layout/media uses $(DIST)/lib as its
                        # EXPORT_LIBRARY
                        desc_dir = export_library
                    else:
                        # Most directories that use this have a relative path
                        # like ".."
                        desc_dir = '%s/%s' % (sandbox.outputdir, export_library)
            if desc_dir:
                print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> %s/%%b | %s" % (output_desc, desc_dir, output_group)

            if sandbox['SDK_LIBRARY'] or sandbox['DIST_INSTALL'] or sandbox['NO_EXPAND_LIBS']:
                print ": %s |> ^ expandlibs_exec.py %%o^ $(PYTHON_PATH) -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/config -I$(MOZ_ROOT)/@(MOZ_OBJDIR)/_virtualenv/lib/python2.7/site-packages $(MOZ_ROOT)/config/expandlibs_exec.py --relative-path $(MOZ_ROOT) --target %%o --extract -- %s %s %%o %s |> %s | %s" % (inputs, sandbox.get_string('AR'), sandbox.get_string('AR_FLAGS'), cmd_inputs, output, output_group)
                print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (output, output_group)

def generate_nss_library(sandbox):
    objs = sandbox['SIMPLE_OBJS']
    # We get OBJ_SUFFIX from config.status, which is just 'o', whereas
    # nss expects it to be '.o', so we fix that here.
    obj_suffix = sandbox.get_string('OBJ_SUFFIX')
    objs = ['%s/%s.%s' % (sandbox.outputdir, o[:-len(obj_suffix)], obj_suffix) for o in objs]
    targets = sandbox['TARGETS']
    objdir = sandbox.get_string('OBJDIR') + '/'

    inputs = ' '.join(objs)

    # See if we should build an archive (.a) file
    library = sandbox.get_string('LIBRARY')
    if library and library in targets:
        output = '%s/%s' % (sandbox.outputdir, library.replace(objdir, ''))
        output_group = '$(MOZ_ROOT)/<-l%s>' % sandbox.get_string('LIBRARY_NAME')
        ar = sandbox.get_string('AR')
        print ": %s |> ^ AR[nss] %%o^ %s %%o %%f |> %s | %s" % (inputs, ar, output, output_group)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (output, output_group)

    # See if we should build a shared library
    shared_library = sandbox.get_string('SHARED_LIBRARY')
    mapfile = sandbox.get_string('MAPFILE')
    if shared_library and shared_library in targets and mapfile:
        output = '%s/%s' % (sandbox.outputdir, shared_library.replace(objdir, ''))

        # First process the map file into something the linker can use
        mapfile = sandbox.get_string('MAPFILE_SOURCE')
        output_mapfile = mapfile + '.processed'
        sandbox.makefile.set_var('<', mapfile)
        sandbox.makefile.set_var('@', output_mapfile)

        process_map_file = sandbox.get_string('PROCESS_MAP_FILE')
        print ": |> ^ Generate %%o^ %s |> %s" % (process_map_file, output_mapfile)

        # Now that we have a proper map file, generate the linker rule
        sandbox.makefile.set_var('@', shared_library)
        sandbox.makefile.set_var('MAPFILE', output_mapfile)

        extra_inputs = output_mapfile
        extra_flags = ""
        for i in ['LD_LIBS', 'EXTRA_LIBS', 'EXTRA_SHARED_LIBS', 'OS_LIBS']:
            resolved_values, lib_deps = resolve_libraries(sandbox, sandbox[i])
            for lib in lib_deps:
                extra_inputs += ' ' + lib
            extra_flags += ' ' + ' '.join(resolved_values)

        extra_inputs += ' $(MOZ_ROOT)/security/nss/<objs>'

        extra_files = ""
        for i in sandbox['SHARED_LIBRARY_DIRS']:
            extra_files += ' ' + os.path.join('%s/%s/*.o' % (sandbox.outputdir, i))

        mkshlib = sandbox.get_string('MKSHLIB')
        print ": %s | %s |> ^ SHLIB %%o^ %s -o %%o %%f %s %s |> %s" % (inputs, extra_inputs, mkshlib, extra_files, extra_flags, output)
        output_group = '$(MOZ_ROOT)/<-l%s%s>' % (sandbox.get_string('LIBRARY_NAME'), sandbox.get_string('LIBRARY_VERSION'))
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (output, output_group)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/bin/%%b | %s" % (output, output_group)

def generate_nsprpub_library(sandbox, objs):
    library_name = sandbox.get_string('LIBRARY_NAME')
    if not library_name:
        return
    library_version = sandbox.get_string('LIBRARY_VERSION')
    lib_suffix = sandbox.get_string('LIB_SUFFIX')
    dll_suffix = sandbox.get_string('DLL_SUFFIX')
    library = '%s/lib%s%s.%s' % (sandbox.outputdir, library_name, library_version, lib_suffix)
    shlib = '%s/lib%s%s.%s' % (sandbox.outputdir, library_name, library_version, dll_suffix)

    sandbox.makefile.set_var('@', library)
    lib_command = sandbox.get_string('AR')
    lib_command += ' ' + sandbox.get_string('AR_FLAGS')
    inputs = ' '.join(objs)
    lib_command += ' ' + inputs
    lib_command += sandbox.get_string('AR_EXTRA_ARGS')
    lib_command += ' && %s %%o' % sandbox.get_string('RANLIB')
    print ": $(MOZ_ROOT)/nsprpub/<objs> |> ^ AR[nsprpub] %%o^ %s |> %s" % (lib_command, library)

    sandbox.makefile.set_var('@', shlib)
    mkshlib = sandbox.get_string('MKSHLIB')
    if mkshlib:
        mkshlib += ' ' + inputs
        flag_group = [
            'RES',
            'LDFLAGS',
            'WRAP_LDFLAGS',
            'EXTRA_LIBS',
        ]
        flags = sandbox.get_tupcpp().get_all_flags(flag_group, shlib)
        lib_flags, deps = resolve_libraries(sandbox, flags)

        deps.append('$(MOZ_ROOT)/nsprpub/<objs>')
        mkshlib += ' ' + ' '.join(lib_flags)
        groups = ' '.join(deps)

        print ": %s |> ^ SHLIB[nsprpub] %%o^ %s |> %s" % (groups, mkshlib, shlib)
        output_group = '$(MOZ_ROOT)/<-l%s%s>' % (library_name, library_version)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/lib/%%b | %s" % (shlib, output_group)
        print ": %s |> ^ INSTALL %%o^ cp %%f %%o |> $(DIST)/bin/%%b | %s" % (shlib, output_group)

def generate_nsprpub_progs(sandbox, objs):
    cc = sandbox.get_string('CC')
    flags = sandbox.get_string('XCFLAGS') + \
            sandbox.get_string('LDFLAGS') + \
            sandbox.get_string('XLDOPTS')
    outoption = sandbox.get_string('OUTOPTION')
    prog_suffix = sandbox.get_string('PROG_SUFFIX')
    obj_suffix = sandbox.get_string('OBJ_SUFFIX')

    # For some reason the space at the end of '-o ' doesn't seem to carry through.
    if outoption == '-o':
        outoption = '-o '

    for prog in sandbox['PROGS']:
        prog = prog.replace('./', '')
        print ": %s/%s |> %s %s %%f %s%%o |> %s/%s | $(MOZ_ROOT)/nsprpub/<progs>" % (sandbox.outputdir, prog + '.' + obj_suffix, cc, flags, outoption, sandbox.outputdir, prog + prog_suffix)

def generate_rules(sandbox, objs):
    if sandbox.relativesrcdir.startswith('nsprpub'):
        if sandbox['PROGS']:
            generate_nsprpub_progs(sandbox, objs)
        else:
            generate_nsprpub_library(sandbox, objs)
    elif sandbox.relativesrcdir.startswith('security/nss'):
        generate_nss_library(sandbox)
    else:
        generate_desc_file(sandbox, objs)
