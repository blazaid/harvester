import harvester
import setuptools

setuptools.setup(
    name='harvester',
    version=harvester.__version__,
    url=harvester.__github_url__,
    license='GNU General Public License v3',
    author='blazaid',
    tests_require=[],
    install_requires=[],
    author_email='alberto.da@gmail.com',
    description='An easy-to-use Web Scraping tool',
    long_description=open('README.rst').read(),
    packages=['harvester'],
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP',
    ],
    extras_require={}
)
