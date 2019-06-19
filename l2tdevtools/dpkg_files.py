# -*- coding: utf-8 -*-
"""Dpkg build files generator."""

from __future__ import unicode_literals

import logging
import os
import shutil
import stat
import time


class DPKGBuildConfiguration(object):
  """Dpkg build configuration.

  Attributes:
    has_bin_directory (bool): True if the Python module creates
        a /usr/bin directory.
    has_egg_info_directory (bool): True if the Python module has
        an .egg_info directory in the dist-packages directory.
    has_egg_info_file (bool): True if the Python module has
        an .egg_info file in the dist-packages directory.
    has_module_source_files (bool): True if the Python module has
        one or more source (*.py) files in the dist-packages directory.
    has_module_shared_object (bool): True if the Python module has
        one or more shared object (*.so) files in the dist-packages directory.
    module_directories (list[str]): module directories in the dist-packages
        directory.
  """

  def __init__(self):
    """Initializes a dpkg build configuration."""
    super(DPKGBuildConfiguration, self).__init__()
    self.has_bin_directory = False
    self.has_egg_info_directory = False
    self.has_egg_info_file = False
    self.has_module_source_files = False
    self.has_module_shared_object = False
    self.module_directories = []


class DPKGBuildFilesGenerator(object):
  """Dpkg build files generator."""

  _EMAIL_ADDRESS = (
      'log2timeline development team <log2timeline-dev@googlegroups.com>')

  _CHANGELOG_TEMPLATE = '\n'.join([
      '{source_package_name:s} ({project_version!s}-1) unstable; urgency=low',
      '',
      '  * Auto-generated',
      '',
      ' -- {maintainer_email_address:s}  {date_time:s}',
      ''])

  _CLEAN_TEMPLATE_PYTHON = '\n'.join([
      '{setup_name:s}/*.pyc',
      '*.pyc',
      ''])

  _COMPAT_TEMPLATE = '\n'.join([
      '9',
      ''])

  _CONTROL_TEMPLATE_CONFIGURE_MAKE = [
      'Source: {source_package_name:s}',
      'Section: libs',
      'Priority: extra',
      'Maintainer: {upstream_maintainer:s}',
      ('Build-Depends: debhelper (>= 9){build_depends:s}'),
      'Standards-Version: 3.9.5',
      'Homepage: {upstream_homepage:s}',
      '',
      'Package: {package_name:s}',
      'Architecture: {architecture:s}',
      'Depends: {depends:s}',
      'Description: {description_short:s}',
      ' {description_long:s}',
      '']

  _CONTROL_TEMPLATE_SETUP_PY_PYTHON2_ONLY = [
      'Source: {source_package_name:s}',
      'Section: python',
      'Priority: extra',
      'Maintainer: {upstream_maintainer:s}',
      'Build-Depends: debhelper (>= 9){build_depends:s}, dh-python',
      'Standards-Version: 3.9.5',
      'X-Python-Version: >= 2.7',
      'Homepage: {upstream_homepage:s}',
      '',
      'Package: {python_package_name:s}',
      'Architecture: {architecture:s}',
      'Depends: {python_depends:s}',
      'Description: {description_short:s}',
      ' {description_long:s}',
      '']

  _CONTROL_TEMPLATE_SETUP_PY_PYTHON3_ONLY = [
      'Source: {source_package_name:s}',
      'Section: python',
      'Priority: extra',
      'Maintainer: {upstream_maintainer:s}',
      'Build-Depends: debhelper (>= 9){build_depends:s}, dh-python',
      'Standards-Version: 3.9.5',
      'X-Python3-Version: >= 3.4',
      'Homepage: {upstream_homepage:s}',
      '',
      'Package: {python_package_name:s}',
      'Architecture: {architecture:s}',
      'Depends: {python3_depends:s}',
      'Description: {description_short:s}',
      ' {description_long:s}',
      '']

  _CONTROL_TEMPLATE_SETUP_PY = [
      'Source: {source_package_name:s}',
      'Section: python',
      'Priority: extra',
      'Maintainer: {upstream_maintainer:s}',
      'Build-Depends: debhelper (>= 9){build_depends:s}, dh-python',
      'Standards-Version: 3.9.5',
      'X-Python-Version: >= 2.7',
      'X-Python3-Version: >= 3.4',
      'Homepage: {upstream_homepage:s}',
      '',
      'Package: {python_package_name:s}',
      'Architecture: {architecture:s}',
      'Depends: {python_depends:s}',
      'Description: Python 2 module of {description_name:s}',
      ' {description_long:s}',
      '',
      'Package: {python3_package_name:s}',
      'Architecture: {architecture:s}',
      'Depends: {python3_depends:s}',
      'Description: Python 3 module of {description_name:s}',
      ' {description_long:s}',
      '']

  _CONTROL_TEMPLATE_SETUP_PY_TOOLS = [
      'Package: {source_package_name:s}-tools',
      'Architecture: all',
      ('Depends: {python_package_name:s} (>= ${{binary:Version}}), '
       'python (>= 2.7~), ${{python:Depends}}, ${{misc:Depends}}'),
      'Description: Tools of {description_name:s}',
      ' {description_long:s}',
      '']

  _COPYRIGHT_TEMPLATE = '\n'.join([
      ''])

  _INSTALL_TEMPLATE_PYTHON_DATA = '\n'.join([
      'data/* usr/share/{package_name:s}',
      ''])

  _INSTALL_TEMPLATE_PYTHON2 = '\n'.join([
      'usr/lib/python2*/dist-packages/{package_name:s}/',
      'usr/lib/python2*/dist-packages/{package_name:s}*.egg-info/*',
      ''])

  _INSTALL_TEMPLATE_PYTHON3 = '\n'.join([
      'usr/lib/python3*/dist-packages/{package_name:s}/',
      'usr/lib/python3*/dist-packages/{package_name:s}*.egg-info/*',
      ''])

  _INSTALL_TEMPLATE_PYTHON_TOOLS = '\n'.join([
      'usr/bin',
      ''])

  _RULES_TEMPLATE_CONFIGURE_MAKE = '\n'.join([
      '#!/usr/bin/make -f',
      '',
      '# Uncomment this to turn on verbose mode.',
      '#export DH_VERBOSE=1',
      '',
      '# This has to be exported to make some magic below work.',
      'export DH_OPTIONS',
      '',
      '%:',
      '\tdh  $@ {build_system:s}{with_quilt:s}',
      '',
      '.PHONY: override_dh_auto_configure',
      'override_dh_auto_configure:',
      '\tdh_auto_configure -- {configure_options:s} CFLAGS="-g"',
      '',
      '.PHONY: override_dh_auto_test',
      'override_dh_auto_test:',
      '',
      '.PHONY: override_dh_install',
      'override_dh_install:',
      '\t# Create the {package_name:s} package.',
      '{install_package:s}',
      '# The {package_name:s}-dbg package is created by dh_strip.',
      '\tdh_install',
      '',
      '.PHONY: override_dh_installmenu',
      'override_dh_installmenu:',
      '',
      '.PHONY: override_dh_installmime',
      'override_dh_installmime:',
      '',
      '.PHONY: override_dh_installmodules',
      'override_dh_installmodules:',
      '',
      '.PHONY: override_dh_installlogcheck',
      'override_dh_installlogcheck:',
      '',
      '.PHONY: override_dh_installlogrotate',
      'override_dh_installlogrotate:',
      '',
      '.PHONY: override_dh_installpam',
      'override_dh_installpam:',
      '',
      '.PHONY: override_dh_installppp',
      'override_dh_installppp:',
      '',
      '.PHONY: override_dh_installudev',
      'override_dh_installudev:',
      '',
      '.PHONY: override_dh_installwm',
      'override_dh_installwm:',
      '',
      '.PHONY: override_dh_installxfonts',
      'override_dh_installxfonts:',
      '',
      '.PHONY: override_dh_gconf',
      'override_dh_gconf:',
      '',
      '.PHONY: override_dh_icons',
      'override_dh_icons:',
      '',
      '.PHONY: override_dh_perl',
      'override_dh_perl:',
      '',
      '.PHONY: override_dh_pysupport',
      'override_dh_pysupport:',
      '',
      '.PHONY: override_dh_strip',
      'override_dh_strip:',
      'ifeq (,$(filter nostrip,$(DEB_BUILD_OPTIONS)))',
      '        dh_strip -p{package_name:s} --dbg-package={package_name:s}-dbg',
      'endif',
      '',
      '.PHONY: override_dh_shlibdeps',
      'override_dh_shlibdeps:',
      '\tdh_shlibdeps -L{package_name:s} -l${{CURDIR}}/debian/tmp/usr/lib',
      ''])

  # Force the build system to setup.py here in case the package ships
  # a Makefile or equivalent.
  _RULES_TEMPLATE_SETUP_PY_PYTHON2_ONLY = '\n'.join([
      '#!/usr/bin/make -f',
      '',
      '%:',
      '\tdh $@ --buildsystem=python_distutils --with=python2{with_quilt:s}',
      '',
      '.PHONY: override_dh_auto_clean',
      'override_dh_auto_clean:',
      '\tdh_auto_clean',
      ('\trm -rf build {setup_name:s}.egg-info/SOURCES.txt '
       '{setup_name:s}.egg-info/PKG-INFO'),
      '',
      '.PHONY: override_dh_auto_install',
      'override_dh_auto_install:',
      '\tdh_auto_install --destdir $(CURDIR)',
      ''])

  # Force the build system to setup.py here in case the package ships
  # a Makefile or equivalent.
  _RULES_TEMPLATE_SETUP_PY_PYTHON3_ONLY = '\n'.join([
      '#!/usr/bin/make -f',
      '',
      '%:',
      '\tdh $@ --buildsystem=python_distutils --with=python3{with_quilt:s}',
      '',
      '.PHONY: override_dh_auto_clean',
      'override_dh_auto_clean:',
      '\tset -ex; for python in $(shell py3versions -r); do \\',
      '\t\t$$python setup.py clean -a; \\',
      '\tdone;',
      ('\trm -rf build {setup_name:s}.egg-info/requires.txt '
       '{setup_name:s}.egg-info/SOURCES.txt '
       '{setup_name:s}.egg-info/PKG-INFO'),
      '',
      '.PHONY: override_dh_auto_build',
      'override_dh_auto_build:',
      '\tset -ex; for python in $(shell py3versions -r); do \\',
      '\t\t$$python setup.py build; \\',
      '\tdone;',
      '',
      '.PHONY: override_dh_auto_install',
      'override_dh_auto_install:',
      '\tset -ex; for python in $(shell py3versions -r); do \\',
      '\t\t$$python setup.py install --root=$(CURDIR) --install-layout=deb; \\',
      '\tdone;',
      ''])

  _RULES_TEMPLATE_SETUP_PY = '\n'.join([
      '#!/usr/bin/make -f',
      '',
      '%:',
      ('\tdh $@ --buildsystem=python_distutils --with=python2,python3'
       '{with_quilt:s}'),
      '',
      '.PHONY: override_dh_auto_clean',
      'override_dh_auto_clean:',
      '\tdh_auto_clean',
      ('\trm -rf build {setup_name:s}.egg-info/SOURCES.txt '
       '{setup_name:s}.egg-info/PKG-INFO'),
      '',
      '.PHONY: override_dh_auto_build',
      'override_dh_auto_build:',
      '\tdh_auto_build',
      '\tset -ex; for python in $(shell py3versions -r); do \\',
      '\t\t$$python setup.py build; \\',
      '\tdone;',
      '',
      '.PHONY: override_dh_auto_install',
      'override_dh_auto_install:',
      '\tdh_auto_install --destdir $(CURDIR)',
      '\tset -ex; for python in $(shell py3versions -r); do \\',
      '\t\t$$python setup.py install --root=$(CURDIR) --install-layout=deb; \\',
      '\tdone;',
      ''])

  _SOURCE_FORMAT_TEMPLATE = '\n'.join([
      '3.0 (quilt)',
      ''])

  _SOURCE_OPTIONS_TEMPLATE = '\n'.join([
      ('extend-diff-ignore = "(^|/)(\\.eggs|config\\.h|config\\.log|'
       'config\\.status|.*\\.egg-info|.*\\.egg-info/.*|Makefile)$"'),
      ''])

  def __init__(
      self, project_definition, project_version, data_path,
      dependency_definitions, build_configuration=None):
    """Initializes a dpkg build files generator.

    Args:
      project_definition (ProjectDefinition): project definition.
      project_version (str): version of the project.
      data_path (str): path to the data directory which contains the dpkg
          templates and patches sub directories.
      dependency_definitions (dict[str, ProjectDefinition]): definitions of all
          projects, which is used to determine the properties of dependencies.
      build_configuration (Optional[DPKGBuildConfiguration]): the dpgk build
          configuration.
    """
    super(DPKGBuildFilesGenerator, self).__init__()
    self._build_configuration = build_configuration
    self._data_path = data_path
    self._dependency_definitions = dependency_definitions
    self._project_definition = project_definition
    self._project_version = project_version
    self._python2_only_dependencies = {}

  def _GenerateFile(
      self, template_filename, template_data, template_values, output_filename):
    """Generates a file based on a template.

    Args:
      template_filename (str): template filename or None if not defined.
          If not defined template_data is used.
      template_data (str): template data.
      template_values (dict[str, str]): template values or None if not defined.
      output_filename (str): name of the resulting file.
    """
    if template_filename:
      template_file_path = os.path.join(
          self._data_path, 'dpkg_templates', template_filename)
      with open(template_file_path, 'rb') as file_object:
        template_data = file_object.read()

      template_data = template_data.decode('utf-8')

    if template_values:
      template_data = template_data.format(**template_values)

    template_data = template_data.encode('utf-8')

    with open(output_filename, 'wb') as file_object:
      file_object.write(template_data)

  def _GenerateChangelogFile(self, dpkg_path):
    """Generates the dpkg build changelog file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    source_package_name = self._GetSourcePackageName()

    timezone_minutes, _ = divmod(time.timezone, 60)
    timezone_hours, timezone_minutes = divmod(timezone_minutes, 60)

    # If timezone_hours is -1 {0:02d} will format as -1 instead of -01
    # hence we detect the sign and force a leading zero.
    if timezone_hours < 0:
      timezone_string = '-{0:02d}{1:02d}'.format(
          -timezone_hours, timezone_minutes)
    else:
      timezone_string = '+{0:02d}{1:02d}'.format(
          timezone_hours, timezone_minutes)

    date_time_string = '{0:s} {1:s}'.format(
        time.strftime('%a, %d %b %Y %H:%M:%S'), timezone_string)

    template_values = {
        'date_time': date_time_string,
        'maintainer_email_address': self._EMAIL_ADDRESS,
        'project_version': self._project_version,
        'source_package_name': source_package_name}

    output_filename = os.path.join(dpkg_path, 'changelog')
    self._GenerateFile(
        None, self._CHANGELOG_TEMPLATE, template_values, output_filename)

  def _GenerateCleanFile(self, dpkg_path):
    """Generates the dpkg build clean file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    # TODO: add support for configure_make

    if self._project_definition.build_system == 'setup_py':
      setup_name = self._GetPythonSetupName()

      template_values = {
          'setup_name': setup_name}

      output_filename = os.path.join(dpkg_path, 'clean')
      self._GenerateFile(
          None, self._CLEAN_TEMPLATE_PYTHON, template_values, output_filename)

  def _GenerateCompatFile(self, dpkg_path):
    """Generates the dpkg build compat file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    output_filename = os.path.join(dpkg_path, 'compat')
    self._GenerateFile(None, self._COMPAT_TEMPLATE, None, output_filename)

  def _GenerateControlFile(self, dpkg_path):
    """Generates the dpkg build control file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    source_package_name = self._GetSourcePackageName()

    package_name = self._GetPackageName(self._project_definition)
    python_package_name, python3_package_name = self._GetPythonPackageNames()

    architecture = self._GetArchitecture()

    python2_only = self._project_definition.IsPython2Only()
    python3_only = self._project_definition.IsPython3Only()

    build_depends = []
    python2_build_depends = []
    python3_build_depends = []

    if self._project_definition.patches:
      build_depends.append('quilt')

    if self._project_definition.build_system == 'configure_make':
      build_depends.append('autotools-dev')

    elif self._project_definition.build_system == 'setup_py':
      build_depends.append('dh-python')

      python2_build_depends.append('python-all (>= 2.7~)')
      python2_build_depends.append('python-setuptools')

      if self._project_definition.architecture_dependent:
        python2_build_depends.append('python-all-dev')

      python3_build_depends.append('python3-all (>= 3.4~)')
      python3_build_depends.append('python3-setuptools')

      if self._project_definition.architecture_dependent:
        python3_build_depends.append('python3-all-dev')

    for dependency in self._project_definition.dpkg_build_dependencies:
      if self._project_definition.build_system == 'setup_py':
        if dependency.startswith('python-'):
          python2_build_depends.append(dependency)

          dependency = 'python3-{0:s}'.format(dependency[7:])
          python3_build_depends.append(dependency)

          continue

      build_depends.append(dependency)

    if (self._project_definition.build_system == 'setup_py' and
        not python3_only):
      build_depends.extend(python2_build_depends)

    if (self._project_definition.build_system == 'setup_py' and
        not python2_only):
      build_depends.extend(python3_build_depends)

    if build_depends:
      build_depends = ', {0:s}'.format(', '.join(build_depends))
    else:
      build_depends = ''

    # description short needs to be a single line.
    description_short = self._project_definition.description_short
    description_short = ' '.join(description_short.split('\n'))

    # description long needs a space at the start of every line after
    # the first.
    description_long = self._project_definition.description_long
    description_long = '\n '.join(description_long.split('\n'))

    depends = []
    python_depends = []
    python3_depends = []

    for dependency in self._project_definition.dpkg_dependencies:
      if dependency.startswith('python-'):
        python_depends.append(dependency)

        if not self._IsPython2OnlyDependency(dependency):
          python3_depends.append('python3-{0:s}'.format(dependency[7:]))
      else:
        depends.append(dependency)

    depends.append('${shlibs:Depends}')
    depends.append('${misc:Depends}')
    depends = ', '.join(depends)

    python_depends.append('${python:Depends}')
    python_depends.append('${misc:Depends}')
    python_depends = ', '.join(python_depends)

    python3_depends.append('${python3:Depends}')
    python3_depends.append('${misc:Depends}')
    python3_depends = ', '.join(python3_depends)

    template_values = {
        'architecture': architecture,
        'build_depends': build_depends,
        'depends': depends,
        'description_long': description_long,
        'description_name': self._project_definition.name,
        'description_short': description_short,
        'package_name': package_name,
        'python_depends': python_depends,
        'python_package_name': python_package_name,
        'python3_depends': python3_depends,
        'python3_package_name': python3_package_name,
        'source_package_name': source_package_name,
        'upstream_homepage': self._project_definition.homepage_url,
        'upstream_maintainer': self._project_definition.maintainer}

    control_template = []
    if self._project_definition.build_system == 'configure_make':
      control_template.extend(self._CONTROL_TEMPLATE_CONFIGURE_MAKE)

    elif self._project_definition.build_system == 'setup_py':
      if python2_only:
        control_template.extend(self._CONTROL_TEMPLATE_SETUP_PY_PYTHON2_ONLY)
      elif python3_only:
        control_template.extend(self._CONTROL_TEMPLATE_SETUP_PY_PYTHON3_ONLY)
      else:
        control_template.extend(self._CONTROL_TEMPLATE_SETUP_PY)

      # TODO: add configuration setting to indicate tools should be packaged.
      if package_name not in ('idna', 'mock', 'psutil'):
        if self._build_configuration.has_bin_directory:
          control_template.extend(self._CONTROL_TEMPLATE_SETUP_PY_TOOLS)

    control_template = '\n'.join(control_template)

    output_filename = os.path.join(dpkg_path, 'control')
    self._GenerateFile(
        self._project_definition.dpkg_template_control, control_template,
        template_values, output_filename)

  def _GenerateCopyrightFile(self, dpkg_path):
    """Generates the dpkg build copyright file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    license_file = os.path.dirname(__file__)
    license_file = os.path.dirname(license_file)
    license_file = os.path.join(
        license_file, 'data', 'licenses', 'LICENSE.{0:s}'.format(
            self._project_definition.name))

    filename = os.path.join(dpkg_path, 'copyright')

    if os.path.exists(license_file):
      shutil.copy(license_file, filename)

    else:
      logging.warning('Missing license file: {0:s}'.format(license_file))
      with open(filename, 'wb') as file_object:
        file_object.write('\n')

  def _GenerateInstallFiles(self, dpkg_path):
    """Generates the dpkg build .install files.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    package_name = self._GetPackageName(self._project_definition)

    # TODO: add support for configure_make
    if self._project_definition.build_system == 'configure_make':
      template_files = (
          self._project_definition.dpkg_template_install or [])

      for template_file in template_files:
        output_filename = os.path.join(dpkg_path, template_file)
        self._GenerateFile(template_file, '', {}, output_filename)

    elif self._project_definition.build_system == 'setup_py':
      # Python modules names contain "_" instead of "-"
      package_name = package_name.replace('-', '_')

      template_values = {'package_name': package_name}

      if not self._project_definition.IsPython3Only():
        self._GeneratePython2ModuleInstallFile(dpkg_path, template_values)

      if not self._project_definition.IsPython2Only():
        self._GeneratePython3ModuleInstallFile(dpkg_path, template_values)

      if self._build_configuration.has_bin_directory:
        install_package_name = self._GetPackageName(self._project_definition)
        output_filename = '{0:s}-tools.install'.format(install_package_name)
        output_filename = os.path.join(dpkg_path, output_filename)
        self._GenerateFile(
            None, self._INSTALL_TEMPLATE_PYTHON_TOOLS, template_values,
            output_filename)

      # TODO: add support for data install files.

  def _GeneratePython2ModuleInstallFile(self, dpkg_path, template_values):
    """Generates the dpkg build Python 2 module .install file.

    Args:
      dpkg_path (str): path to the dpkg files.
      template_values (dict[str, str]): template values or None if not defined.
    """
    python2_package_name, _ = self._GetPythonPackageNames()

    template_files = (
        self._project_definition.dpkg_template_install_python2 or [None])

    for template_file in template_files:
      if template_file:
        output_filename = template_file
        template_data = None
      else:
        output_filename = '{0:s}.install'.format(python2_package_name)
        if not self._build_configuration:
          template_data = self._INSTALL_TEMPLATE_PYTHON2
        else:
          template_data = []

          if self._build_configuration.has_module_source_files:
            template_data.append('usr/lib/python2*/dist-packages/*.py')
          if self._build_configuration.has_module_shared_object:
            template_data.append('usr/lib/python2*/dist-packages/*.so')

          module_directories = self._build_configuration.module_directories
          template_data.extend([
              'usr/lib/python2*/dist-packages/{0:s}'.format(
                  module_directory)
              for module_directory in module_directories])

          if self._build_configuration.has_egg_info_directory:
            template_data.append(
                'usr/lib/python2*/dist-packages/*.egg-info/*')

          elif self._build_configuration.has_egg_info_file:
            template_data.append(
                'usr/lib/python2*/dist-packages/*.egg-info')

          template_data = '\n'.join(template_data)

      output_filename = os.path.join(dpkg_path, output_filename)
      self._GenerateFile(
          template_file, template_data, template_values, output_filename)

  def _GeneratePython3ModuleInstallFile(self, dpkg_path, template_values):
    """Generates the dpkg build Python 3 module .install file.

    Args:
      dpkg_path (str): path to the dpkg files.
      template_values (dict[str, str]): template values or None if not defined.
    """
    _, python3_package_name = self._GetPythonPackageNames()

    template_files = (
        self._project_definition.dpkg_template_install_python3 or [None])

    for template_file in template_files:
      if template_file:
        output_filename = template_file
        template_data = None
      else:
        output_filename = '{0:s}.install'.format(python3_package_name)
        if not self._build_configuration:
          template_data = self._INSTALL_TEMPLATE_PYTHON3
        else:
          template_data = []

          if self._build_configuration.has_module_source_files:
            template_data.append('usr/lib/python3*/dist-packages/*.py')
          if self._build_configuration.has_module_shared_object:
            template_data.append('usr/lib/python3*/dist-packages/*.so')

          module_directories = self._build_configuration.module_directories
          template_data.extend([
              'usr/lib/python3*/dist-packages/{0:s}'.format(
                  module_directory)
              for module_directory in module_directories])

          if self._build_configuration.has_egg_info_directory:
            template_data.append(
                'usr/lib/python3*/dist-packages/*.egg-info/*')

          elif self._build_configuration.has_egg_info_file:
            template_data.append(
                'usr/lib/python3*/dist-packages/*.egg-info')

          template_data = '\n'.join(template_data)

      output_filename = os.path.join(dpkg_path, output_filename)
      self._GenerateFile(
          template_file, template_data, template_values, output_filename)

  def _GenerateRulesFile(self, dpkg_path):
    """Generates the dpkg build rules file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    if self._project_definition.build_system == 'configure_make':
      self._GenerateConfigureMakeRulesFile(dpkg_path)

    elif self._project_definition.build_system == 'setup_py':
      self._GenerateSetupPyRulesFile(dpkg_path)

    filename = os.path.join(dpkg_path, 'rules')
    stat_info = os.stat(filename)
    os.chmod(filename, stat_info.st_mode | stat.S_IEXEC)

  def _GenerateConfigureMakeRulesFile(self, dpkg_path):
    """Generates the dpkg build rules file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    package_name = self._GetPackageName(self._project_definition)

    build_system = '--buildsystem=autoconf'

    if self._project_definition.patches:
      with_quilt = ' --with quilt'
    else:
      with_quilt = ''

    configure_options = ''
    if self._project_definition.dpkg_configure_options:
      configure_options = ' '.join(
          self._project_definition.dpkg_configure_options)

    elif self._project_definition.configure_options:
      configure_options = ' '.join(
          self._project_definition.configure_options)

    install_package = [
        'debian/tmp/usr/lib/lib*.so.*.*.*']

    lines = []
    for glob_pattern in install_package:
      lines.append('\tdh_install "{0:s}" -p {1:s}'.format(
          glob_pattern, install_package))

    install_package = '\n'.join(lines)

    template_values = {
        'build_system': build_system,
        'configure_options': configure_options,
        'install_package': install_package,
        'package_name': package_name,
        'with_quilt': with_quilt}

    output_filename = os.path.join(dpkg_path, 'rules')
    self._GenerateFile(
        self._project_definition.dpkg_template_rules,
        self._RULES_TEMPLATE_CONFIGURE_MAKE, template_values, output_filename)

  def _GenerateSetupPyRulesFile(self, dpkg_path):
    """Generates the dpkg build rules file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    setup_name = self._GetPythonSetupName()

    if self._project_definition.patches:
      with_quilt = ' --with quilt'
    else:
      with_quilt = ''

    template_values = {
        'setup_name': setup_name,
        'with_quilt': with_quilt}

    if self._project_definition.IsPython2Only():
      rules_template = self._RULES_TEMPLATE_SETUP_PY_PYTHON2_ONLY
    elif self._project_definition.IsPython3Only():
      rules_template = self._RULES_TEMPLATE_SETUP_PY_PYTHON3_ONLY
    else:
      rules_template = self._RULES_TEMPLATE_SETUP_PY

    # TODO: replace manual write of rules file by call to _GenerateFile.
    template_filename = self._project_definition.dpkg_template_rules
    if template_filename:
      template_file_path = os.path.join(
          self._data_path, 'dpkg_templates', template_filename)
      with open(template_file_path, 'rb') as file_object:
        rules_template = file_object.read()

      rules_template = rules_template.decode('utf-8')

    output_filename = os.path.join(dpkg_path, 'rules')
    with open(output_filename, 'wb') as file_object:
      data = rules_template.format(**template_values)
      file_object.write(data.encode('utf-8'))

  def _GenerateSourceFormatFile(self, dpkg_path):
    """Generates the dpkg build source/format file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    template_file = self._SOURCE_FORMAT_TEMPLATE

    output_filename = os.path.join(dpkg_path, 'source', 'format')

    self._GenerateFile(None, template_file, None, output_filename)

  def _GenerateSourceOptionsFile(self, dpkg_path):
    """Generates the dpkg build source/options file.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    template_file = self._SOURCE_OPTIONS_TEMPLATE

    output_filename = os.path.join(dpkg_path, 'source', 'options')

    self._GenerateFile(None, template_file, None, output_filename)

  def _GetArchitecture(self):
    """Retrieves the architecture.

    Returns:
      str: architecture.
    """
    if not self._project_definition.architecture_dependent:
      return 'all'

    return 'any'

  def _GetPackageName(self, project_definition):
    """Retrieves the package name.

    Args:
      project_definition (ProjectDefinition): project definition.

    Returns:
      str: package name.
    """
    if project_definition.dpkg_name:
      package_name = project_definition.dpkg_name
    else:
      package_name = project_definition.name

    if package_name.startswith('python-'):
      package_name = package_name[7:]

    return package_name

  def _GetPythonPackageNames(self):
    """Retrieves the Python package names.

    Returns:
      tuple: contains:
        str: Python 2 package name.
        str: Python 3 package name.
    """
    if self._project_definition.dpkg_name:
      package_name = self._project_definition.dpkg_name
    else:
      package_name = self._project_definition.name

    python2_package_name = package_name

    if package_name.startswith('python-'):
      package_name = package_name[7:]

    if not self._project_definition.dpkg_name:
      python2_package_name = 'python-{0:s}'.format(package_name)

    python3_package_name = 'python3-{0:s}'.format(package_name)

    return python2_package_name, python3_package_name

  def _GetPythonSetupName(self):
    """Retrieves the Python setup.py name.

    Returns:
      str: setup.py name.
    """
    if self._project_definition.setup_name:
      return self._project_definition.setup_name

    return self._project_definition.name

  def _GetSourcePackageName(self):
    """Retrieves the source package name.

    Returns:
      str: source package name.
    """
    if self._project_definition.dpkg_source_name:
      return self._project_definition.dpkg_source_name

    return self._project_definition.name

  def _IsPython2OnlyDependency(self, dependency):
    """Checks if a dependency is Python 2 only.

    Args:
      dependency (str): name of the dependency.

    Returns:
      bool: True if Python 2 only, False if not or None if dependency
          was not found.
    """
    if not self._python2_only_dependencies:
      for definition in self._dependency_definitions.values():
        if definition.IsPython2Only():
          package_name = self._GetPackageName(definition)
          self._python2_only_dependencies[package_name] = definition

    return dependency in self._python2_only_dependencies

  def GenerateFiles(self, dpkg_path):
    """Generates the dpkg build files.

    Args:
      dpkg_path (str): path to the dpkg files.
    """
    os.mkdir(dpkg_path)
    self._GenerateChangelogFile(dpkg_path)
    self._GenerateCleanFile(dpkg_path)
    self._GenerateCompatFile(dpkg_path)
    self._GenerateControlFile(dpkg_path)
    self._GenerateCopyrightFile(dpkg_path)
    self._GenerateInstallFiles(dpkg_path)
    self._GenerateRulesFile(dpkg_path)

    os.mkdir(os.path.join(dpkg_path, 'source'))
    self._GenerateSourceFormatFile(dpkg_path)
    self._GenerateSourceOptionsFile(dpkg_path)

    if self._project_definition.patches:
      patches_directory = os.path.join(dpkg_path, 'patches')
      os.mkdir(patches_directory)

      current_path = os.getcwd()
      os.chdir(patches_directory)

      patch_filenames = []
      for patch_filename in self._project_definition.patches:
        filename = os.path.join(self._data_path, 'patches', patch_filename)
        if not os.path.exists(filename):
          logging.warning('Missing patch file: {0:s}'.format(filename))
          continue

        shutil.copy(filename, patch_filename)
        patch_filenames.append(patch_filename)

      os.chdir(current_path)

      filename = os.path.join(dpkg_path, 'patches', 'series')
      with open(filename, 'wb') as file_object:
        data = '\n'.join(patch_filenames)
        file_object.write(data.encode('utf-8'))
