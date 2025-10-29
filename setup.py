from setuptools import setup, find_packages
from setuptools.command.install import install
from version import get_git_version
import os
import subprocess
import sys

def get_requirements():
    thelibFolder = os.path.dirname(os.path.realpath(__file__))
    requirementPath = thelibFolder + '/requirements.txt'
    if os.path.isfile(requirementPath):
        with open(requirementPath) as f:
            return f.read().splitlines()

class PostInstallCommand(install):
    """Post-installation command to generate schema"""
    def run(self):
        install.run(self)
        # Generate schema after installation
        try:
            subprocess.check_call([sys.executable, '-c', 
                'from conduit.schema_generator import main; main()'])
            print("Pipeline schema generated successfully")
        except Exception as e:
            print(f"Warning: Could not generate schema: {e}")

setup(
    name='conduit',
    version=get_git_version(),
    description='Streaming, declarative pipelined data processing library for Python',
    url='https://github.com/aniongithub/conduit/',
    author='Ani Balasubramaniam',
    author_email='ani@anionline.me',
    license='MIT',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=get_requirements(),
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',  
        'Operating System :: POSIX :: Linux',        
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    scripts=['conduit-cli'],
    entry_points={
        'console_scripts': [
            'conduit-generate-schema=conduit.schema_generator:main',
        ]
    },
    cmdclass={
        'install': PostInstallCommand,
    }
)