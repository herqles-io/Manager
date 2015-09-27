from setuptools import setup, find_packages

setup(
    name='hq-manager',
    version='2.0.0.dev1',
    url='https://github.com/herqles-io/hq-manager',
    include_package_data=True,
    license='MIT',
    author='CoverMyMeds',
    description='Herqles Manager',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=[
        'hq-lib==2.0.0.dev1',
        'pika',
        'cherrypy==3.8.0',
        'pyyaml==3.11',
        'Routes==2.2',
        'schematics==1.1.0'
    ],
    scripts=['bin/hq-manager']
)
