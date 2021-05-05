#!/bin/bash
# debian: sudo apt install python3-pip python3-setuptools
# fedora: sudo dnf install python3-devel

cd "$(dirname "$0")"
version="1.2.0"
rm -rf builder/


# copy to a tmp directory
mkdir builder
mkdir builder/radexreader-${version}

cp -r ../src/*  builder/radexreader-${version}/
cp ../README.md builder/radexreader-${version}/
cp /usr/share/common-licenses/GPL-2              builder/radexreader-${version}/LICENSE
mv builder/radexreader-${version}/radexreader.py builder/radexreader-${version}/radexreader/
sed -i 's/python3-radexreader /python3-radexreader-pypi /g' builder/radexreader-${version}/radexreader/radexreader.py
sed -i 's/Usage: radexreader /Usage: radexreader.py /g'     builder/radexreader-${version}/radexreader/radexreader.py













# create package (https://packaging.python.org/tutorials/packaging-projects/)
cd builder/radexreader-${version}/
python3 -m pip install --user --upgrade setuptools wheel --no-warn-script-location
python3 setup.py sdist bdist_wheel
cd ../..
mv builder/radexreader-${version}/dist/* .
echo "==========================="
ls -dltrh $PWD/*.gz $PWD/*.whl
echo "==========================="

# cleanup
rm -r builder/