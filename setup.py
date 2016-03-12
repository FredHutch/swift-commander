from setuptools import setup

__version__ = "1.3.7"

try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Environment :: OpenStack",
    "Intended Audience :: Customer Service",
    "Intended Audience :: Developers",
    "Intended Audience :: Education",
    "Intended Audience :: End Users/Desktop",
    "Intended Audience :: Healthcare Industry",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Science/Research",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: Apache Software License",
    "Natural Language :: English",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: POSIX",
    "Operating System :: POSIX :: Linux",
    "Operating System :: POSIX :: Other",
    "Operating System :: Unix",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Programming Language :: Unix Shell",
    "Topic :: Desktop Environment :: File Managers",
    "Topic :: Internet",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Topic :: System :: Archiving",
    "Topic :: System :: Archiving :: Backup",
    "Topic :: System :: Filesystems",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Systems Administration",
    "Topic :: Utilities"
]

setup(
    name='swift-commander',
    version=__version__,
    description='''\
swift commander (swc) is a wrapper to various command line
client tools for openstack swift cloud storage systems.''',
    long_description=read_md('README.md'),
    packages=['swift_commander'],
    scripts=['swift_commander/swc'],
    author = 'Dirk Petersen, Jeff Katcher',
    author_email = 'dp@nowhere.com',
    url = 'https://github.com/FredHutch/swift-commander', 
    download_url = 'https://github.com/FredHutch/swift-commander/tarball/%s' % __version__,
    keywords = ['openstack', 'swift', 'cloud storage'], # arbitrary keywords
    classifiers = CLASSIFIERS,
    # 'python-swiftclient>=2.5,<3','python-keystoneclient>=1.5,<2'
    install_requires=[
        'python-swiftclient>=2.5,<3', 
        'python-keystoneclient>=1.5,<2'
        ],
    entry_points={
        # we use console_scripts here to allow virtualenv to rewrite shebangs
        # to point to appropriate python and allow experimental python 2.X
        # support.
        'console_scripts': [
            'swbundler.py=swift_commander.swbundler:main',
            'swfoldersize.py=swift_commander.swfoldersize:main',
            'swhashcomp.py=swift_commander.swhashcomp:main',
            'swpget.py=swift_commander.swpget:main',
            'swrm.py=swift_commander.swrm:main',
            'swsearch.py=swift_commander.swsearch:main',
            'swsymlinks.py=swift_commander.swsymlinks:main',
        ]
    }
)
