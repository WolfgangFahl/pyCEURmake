from setuptools import setup
from collections import OrderedDict
from ceurws.version import Version
setup(name=Version.name,
      version=Version.version,
      description=Version.description,
      long_description_content_type='text/markdown',
      url='https://github.com/WolfgangFahl/pyCEURmake',
      download_url='https://github.com/WolfgangFahl/pyCEURmake',
      author='wf',
      license='Apache',
      project_urls=OrderedDict(
        (
            ("Code", "https://github.com/WolfgangFahl/pyCEURmake"),
            ("Issue tracker", "https://github.com/WolfgangFahl/pyCEURmake/issues"),
        )
      ),
      classifiers=[
            'Programming Language :: Python',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9'
      ],
      packages=['ceurws'],
      package_data={'ceurws': ['resources/templates/*.jinja','resources/templates/*.html']},
      install_requires=[
          'pylodstorage>=0.0.69',
          'python-dateutil',
          'ConferenceCorpus>=0.0.26',
          'pyFlaskBootstrap4>=0.2.13',
          'wikirender>=0.0.33',
          'flask-dropzone',
          'odfpy'
      ],
      entry_points={
         'console_scripts': [
             'pyCEURmake = ceurws.webserver:main',
      ],
    },
      zip_safe=False)
