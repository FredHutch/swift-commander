#! /bin/bash

version=$(grep ^__version__ setup.py | cut -d'"' -f2)

git commit -a -m "version ${version}"
git tag ${version} -m "tag for PyPI"
git push --tags origin master
python3 setup.py register -r pypitest
python3 setup.py sdist upload -r pypitest

