rm -rf .cache/
rm -rf *.egg-info
rm -rf build/
rm -rf dist/

python setup.py sdist bdist bdist_wheel
python setup.py sdist upload

rm -rf .cache/
rm -rf *.egg-info
rm -rf build/
rm -rf dist/
