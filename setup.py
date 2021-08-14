#!/usr/bin/env python3

from setuptools import setup

setup(name='flickr-cache',
      python_requires='>=3',
      install_requires = ['flickrapi'],
      version='0.1',
      description='cache for flickrapi',
      author='Magnus Hagdorn',
      author_email='magnus.hagdorn@marsupium.org',
      url='https://github.com/mhagdorn/flickr-cache',
      packages=['flickr_cache'],
  )
