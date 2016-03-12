#! /bin/bash

version=$(grep ^__version__ setup.py | cut -d'"' -f2)

git commit -a -m "version ${version}"
git tag ${version} -m "tag for PyPI"
git push --tags origin master
python3 setup.py register -r pypi
python3 setup.py sdist upload -r pypi

echo "  Done! Occasionally you may want to remove older tags:"
echo "git tag 1.2.3 -d"
echo "git push origin :refs/tags/1.2.3"



