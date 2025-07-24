from setuptools import setup, find_packages

setup(
    name='perfectpixel',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Flask',
        'requests',
        'beautifulsoup4',
        'chardet',
        'lxml'
    ],
    entry_points={
        'console_scripts': [
            'perfectpixel=perfectpixel.app:app.run',
        ],
    }
)
