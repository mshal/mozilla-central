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
    print ": foreach %s | %s |> ^ Preprocessor %%f -> %%o^ $(PYTHON) $(MOZ_ROOT)/config/Preprocessor.py %s %%f > %%o |> %s/%%b | %s" % (filename, input_group, flags, output_path, output_group)

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

    accessfu_files = sandbox['ACCESSFU_FILES']
    for export in accessfu_files:
        generate_install_rule(sandbox, export, os.path.join(final_target,
                                                   'modules',
                                                   'accessibility'))

    install_targets = sandbox['INSTALL_TARGETS']
    for target in install_targets:
        # TODO: Currently only some targets are supported
        if target in ('EXPORTS_GENERATED', 'BRANDING', 'SYNC_MAIN', 'SYNC_ENGINES', 'SYNC_STAGES', 'WORKER', 'MODULES', 'CRYPTO_MODULE', 'globalgen_headers'):
            files = sandbox['%s_FILES' % target]
            dest = sandbox.get_string('%s_DEST' % target)
            for f in files:
                generate_install_rule(sandbox, f, dest)

    pp_targets = sandbox['PP_TARGETS']
    for target in pp_targets:
        # TODO: Currently only some targets are supported
        if target in ('SEARCHPLUGINS', 'PP_JS_MODULES', 'SYNC_PP', 'MAIN_JS_MODULE', 'MODULES'):
            files = sandbox[target]
            dest = sandbox.get_string('%s_PATH' % target)
            for f in files:
                prefix = ""
                if target == 'SEARCHPLUGINS':
                    # SEARCHPLUGINS uses vpath to locate the xml. Ugh.
                    prefix = 'en-US/searchplugins/'
                flags = sandbox['%s_FLAGS' % target]
                generate_pp_rule(sandbox, prefix + f, defines, flags, dest)

    # Files manually exported to dist/bin/res
    for target in sandbox['EXPORT_RESOURCE']:
        generate_install_rule(sandbox, target, '$(DIST)/bin/res')
    for target in sandbox['EXPORT_RESOURCE_CONTENT']:
        generate_install_rule(sandbox, target, '$(DIST)/bin/res/dtd')
