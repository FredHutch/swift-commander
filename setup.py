from setuptools import setup

CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Natural Language :: English",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Topic :: Cloud Storage :: Libraries :: Python Modules",
]

setup(
    name='swift-commander',
    version='1.3',
    description='''\
swift commander (swc) is a wrapper to various command line
client tools for openstack swift cloud storage systems.''',
    packages=['swift_commander'],
    scripts=['swift_commander/swc'],
    author = 'Dirk Petersen, Jeff Katcher',
    author_email = 'dp@nowhere.com',
    url = 'https://github.com/FredHutch/swift-commander', 
    download_url = 'https://github.com/FredHutch/swift-commander/tarball/1.3',
    keywords = ['openstack', 'swift', 'cloud storage'], # arbitrary keywords
    classifiers = CLASSIFIERS,
    install_requires=['python-swiftclient>=2.5,<3', 'python-keystoneclient>=1.5,<2']
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

