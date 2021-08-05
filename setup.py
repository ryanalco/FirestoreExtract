from setuptools import setup

requirements_file = "requirements.txt"

setup(name='popl',
      version='0.0.1',
      description='Popl google cloud functions',
      install_requires=open(requirements_file).readlines(),
)