#!/usr/bin/env python

import fnmatch
import os
import subprocess

from distutils.core import Command
from setuptools import setup, find_packages
from sphinx.setup_command import BuildDoc

THIS_PATH = os.path.dirname(__file__)


class PublishDocsToGitHubPages(Command):
    description = 'Deploy built documentation to GitHub Pages'
    user_options = [
            ('repo=', 'r', 'Repository URL'),
            ('docs-dir=', 'd', 'Directory of documentation to publish'),
            ('commit-msg=', 'm', 'Commit message')
        ]

    def initialize_options(self):
        self.repo = None
        self.docs_dir = None
        self.commit_msg = None

    def finalize_options(self):
        self.repo = 'git@github.com:mantidproject/mantidimaging.git' \
            if self.repo is None else self.repo

        self.docs_dir = 'docs/build/html' \
            if self.docs_dir is None else self.docs_dir

        self.commit_msg = 'Publish documentation' \
            if self.commit_msg is None else self.commit_msg

    def run(self):
        git_dir = os.path.join(self.docs_dir, '.git')
        if os.path.exists(git_dir):
            import shutil
            shutil.rmtree(git_dir)

        from git import Git
        g = Git(self.docs_dir)
        g.init()
        g.add('.')
        g.commit('-m {}'.format(self.commit_msg))
        g.push('--force', self.repo, 'master:gh-pages')


class GenerateSphinxApidoc(Command):
    description = 'Generate API documentation with sphinx-apidoc'
    user_options = []

    def initialize_options(self):
        self.sphinx_options = []
        self.module_dir = None
        self.out_dir = None

    def finalize_options(self):
        self.sphinx_options.append('sphinx-apidoc')
        self.sphinx_options.extend(['-f', '-M', '-e', '-T'])

        self.sphinx_options.extend(['-d', '10'])

        self.module_dir = 'mantidimaging'
        self.sphinx_options.append(self.module_dir)

        self.out_dir = 'docs/api/'
        self.sphinx_options.extend(['-o', self.out_dir])

    def run(self):
        print('Running: {}'.format(' '.join(self.sphinx_options)))
        subprocess.call(self.sphinx_options)


class CompilePyQtUiFiles(Command):
    description = 'Compiles any PyQt .ui files found in the source tree'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    @staticmethod
    def compile_single_file(ui_filename):
        from PyQt5 import uic
        py_filename = os.path.splitext(ui_filename)[0] + '.py'
        with open(py_filename, 'w') as py_file:
            uic.compileUi(ui_filename, py_file)

    @staticmethod
    def find_ui_files():
        matches = []
        for root, dirnames, filenames in os.walk('./mantidimaging/'):
            for filename in fnmatch.filter(filenames, '*.ui'):
                matches.append(os.path.join(root, filename))
        return matches

    def run(self):
        ui_files = self.find_ui_files()
        for f in ui_files:
            self. compile_single_file(f)

setup(
    name='mantidimaging',
    version='0.9',
    packages=find_packages(),
    package_data={
        'mantidimaging.gui': ['ui/*.ui']
    },
    py_modules=['mantidimaging'],
    entry_points={
        'console_scripts': [
            'mantidimaging = mantidimaging.main:cli_main',
            'mantidimaging-ipython = mantidimaging.ipython:main'
        ],
        'gui_scripts': [
            'mantidimaging-gui = mantidimaging.main:gui_main'
        ]
    },
    url='https://github.com/mantidproject/mantidimaging',
    license='GPL-3.0',
    author='Dimitar Tasev',
    author_email='dimitar.tasev@stfc.ac.uk',
    description='MantidImaging Tomographic Reconstruction package',
    long_description=open("README.md").read(),
    platforms=["Linux"],
    test_suite='nose.collector',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Natural Language :: English',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Topic :: Scientific/Engineering',
        'Topic :: Imaging',
        'Topic :: Tomographic Reconstruction',
    ],
    cmdclass={
        'docs_api': GenerateSphinxApidoc,
        'docs': BuildDoc,
        'docs_publish': PublishDocsToGitHubPages,
        'compile_ui': CompilePyQtUiFiles
    }
)
