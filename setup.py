from setuptools import setup

setup(
    name='swift-commander',
    version='0.0.1',
    description='''\
swift commander (swc) is a wrapper to various command line
client tools for openstack swift cloud storage systems.''',
    packages=['swc'],
    scripts=['swc/swc'],
    entry_points={
        # we use console_scripts here to allow virtualenv to rewrite shebangs
        # to point to appropriate python and allow experimental python 2.X
        # support.
        'console_scripts': [
            'swbundler.py=swc.swbundler:main',
            'swfoldersize.py=swc.swfoldersize:main',
            'swhashcomp.py=swc.swhashcomp:main',
            'swpget.py=swc.swpget:main',
            'swrm.py=swc.swrm:main',
            'swsearch.py=swc.swsearch:main',
            'swsymlinks.py=swc.swsymlinks:main',
        ]
    }
)
