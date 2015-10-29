rm -rf .cache/
rm -rf *.egg-info
rm -rf build/
rm -rf dist/

python setup.py sdist bdist bdist_wheel
twine upload dist/*

rm -rf .cache/
rm -rf *.egg-info
rm -rf build/
rm -rf dist/
