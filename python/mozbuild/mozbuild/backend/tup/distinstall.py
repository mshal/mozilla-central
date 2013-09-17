#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

def get_output_group(sandbox):
    xpi_name = sandbox.get_string('XPI_NAME')
    if xpi_name:
        group_suffix = "-xpi-%s" % xpi_name
    else:
        dist_subdir = sandbox.get_string('DIST_SUBDIR')
        if dist_subdir:
            group_suffix = "-%s" % dist_subdir
        else:
            group_suffix = ""
    return '$(MOZ_ROOT)/<installed-manifests%s>' % group_suffix

def generate_pp_rule(sandbox, filename, defines, extra_flags, output_path, input_group=""):
    flags = ' '.join(defines)
    if(extra_flags):
        flags += ' ' + ' '.join(extra_flags)
    output_group = ""
    if filename.endswith('.manifest'):
        output_group = get_output_group(sandbox)
    output_file = os.path.basename(filename)
    if output_file.endswith('.in'):
        output_file, ext = os.path.splitext(output_file)
    print ": foreach %s | %s |> ^ Preprocessor %%f -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %%f > %%o |> %s/%s | %s" % (filename, input_group, flags, output_path, output_file, output_group)

def generate_install_rule(sandbox, filename, output_path):
    output_group = ""
    if filename.endswith('.manifest'):
        output_group = get_output_group(sandbox)
    elif filename.endswith('.h'):
        output_group = "$(MOZ_ROOT)/<installed-headers>"
    elif filename.endswith('.png'):
        # This is to help browser/app/Makefile.in copy pngs from
        # $(DIST)/branding to $(FINAL_TARGET)/chrome/icons/default
        output_group = "$(MOZ_ROOT)/<installed-icons>"
    print ": foreach %s |> !cp |> %s/%%b | %s" % (filename, output_path, output_group)

def generate_rules(sandbox):
    final_target = sandbox.get_string('FINAL_TARGET')
    defines = sandbox['DEFINES']
    defines.extend(sandbox['ACDEFINES'])

    component_dir = os.path.join(final_target, 'components')
    js_module_dir = sandbox.get_string('JS_MODULES_PATH')
    if not js_module_dir:
        js_module_dir = 'modules'
    js_module_dir = os.path.join(final_target, js_module_dir)

    extra_pp_components = sandbox['EXTRA_PP_COMPONENTS']
    extra_pp_components_flags = sandbox['EXTRA_PP_COMPONENTS_FLAGS']
    for component in extra_pp_components:
        generate_pp_rule(sandbox, component, defines, extra_pp_components_flags, component_dir, input_group="$(MOZ_ROOT)/<generated-headers>")

    pref_js_exports = sandbox['PREF_JS_EXPORTS']
    if sandbox['GRE_MODULE']:
        pref_dir = 'greprefs'
    elif sandbox['XPI_NAME'] or sandbox['LIBXUL_SDK'] or sandbox['DIST_SUBDIR']:
        pref_dir = 'defaults/preferences'
    else:
        pref_dir = 'defaults/pref'
    pref_pp_flags = sandbox['PREF_PP_FLAGS']
    if sandbox['OS_ARCH'] == 'WINNT':
        # on win32, pref files need CRLF line endings... see bug 206029
        pref_pp_flags.append('--line-endings=crlf')
    for export in pref_js_exports:
        generate_pp_rule(sandbox, export, defines, pref_pp_flags, os.path.join(final_target, pref_dir))

    extra_components = sandbox['EXTRA_COMPONENTS']
    for component in extra_components:
        generate_install_rule(sandbox, component, component_dir)

    extra_js_modules = sandbox['EXTRA_JS_MODULES']
    for module in extra_js_modules:
        fullpath = sandbox.vpath_resolve(module)
        generate_install_rule(sandbox, fullpath, js_module_dir)

    extra_pp_js_modules = sandbox['EXTRA_PP_JS_MODULES']
    for module in extra_pp_js_modules:
        generate_pp_rule(sandbox, module, defines, [], js_module_dir)

    autocfg_js_exports = sandbox['AUTOCFG_JS_EXPORTS']
    autocfg_dest = os.path.join(final_target, 'defaults', 'autoconfig')
    for export in autocfg_js_exports:
        generate_install_rule(sandbox, export, autocfg_dest)

    pp_targets = sandbox['PP_TARGETS']
    for target in pp_targets:
        files = sandbox[target]
        dest = sandbox.get_string('%s_PATH' % target)
        if not dest:
            dest = sandbox.outputdir
        for f in files:
            prefix = ""
            if target == 'SEARCHPLUGINS':
                # SEARCHPLUGINS uses vpath to locate the xml. Ugh.
                prefix = 'en-US/searchplugins/'
            flags = sandbox['%s_FLAGS' % target]
            generate_pp_rule(sandbox, prefix + f, defines, flags, dest)

    install_targets = sandbox['INSTALL_TARGETS']

    if 'NSINSTALL' in install_targets:
        # For some reason nsinstall is linked as nsinstall_real, then copied
        # to nsinstall, then installed.
        input_file = "%s/%s" % (sandbox.outputdir,
                                sandbox.get_string('HOST_PROGRAM'))
        output_file = "%s/nsinstall%s" % (sandbox.outputdir,
                                          sandbox.get_string('HOST_BIN_SUFFIX'))
        print ": %s |> cp %%f %%o |> %s" % (input_file, output_file)

    # Files that exist in the objdir
    obj_files = ('xpcom-config.h',
                 'js-config.h',
                 'cairo-features.h',
                 'necko-config.h',
                 'nsinstall')
    for target in install_targets:
        if target == 'NSINSTALL' and sandbox.relativesrcdir == 'js/src/config':
            # Both js/src/config/ and config/ try to create nsinstall, but we
            # only need one.
            continue
        # TODO: Currently only some targets are supported
        # GDBINIT: has hidden '.gdbinit' path
        if target in ('EXPORTS_GENERATED', 'BRANDING', 'SYNC_MAIN', 'SYNC_ENGINES', 'SYNC_STAGES', 'WORKER', 'MODULES', 'CRYPTO_MODULE', 'globalgen_headers', 'xpcom', 'jsconfig', 'histoenums', 'extra_export_files', 'structlist', 'cairo_features', 'neckoconfig', 'errorlist', 'GDB_INSTALL_AUTOLOAD', 'SHELL_INSTALL_AUTOLOAD', 'SHELL_INSTALL_AUTOLOAD_SCRIPT', 'xpcaccevents', 'ACCESSFU', 'HEADERS', 'TEST_PLUGIN', 'ICON', 'NSINSTALL'):
            files = sandbox['%s_FILES' % target]
            dest = sandbox.get_string('%s_DEST' % target)
            for f in files:
                if f in obj_files:
                    generate_install_rule(sandbox, os.path.join(sandbox.outputdir, f), dest)
                else:
                    generate_install_rule(sandbox, f, dest)

    # Files manually exported to dist/bin/res
    for target in sandbox['EXPORT_RESOURCE']:
        generate_install_rule(sandbox, target, '$(DIST)/bin/res')
    for target in sandbox['EXPORT_RESOURCE_CONTENT']:
        generate_install_rule(sandbox, target, '$(DIST)/bin/res/dtd')
