from setuptools import setup

setup(
    name='swift-commander',
    version='0.0.1',
    description='''\
swift commander (swc) is a wrapper to various command line
client tools for openstack swift cloud storage systems.''',
    packages=['swift_commander'],
    scripts=['swift_commander/swc'],
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
