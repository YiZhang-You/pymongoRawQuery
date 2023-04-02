from distutils.core import setup
import setuptools

packages = ['pymongoRawQuery']  # 唯一的包名，自己取名
setup(
      name='pymongoRawQuery',
      version='1.0.1',
      description='mongo raw query',
      author='YiZhang-You',
      author_email='yyz18071720400@163.com',
      packages=packages,
      package_dir={'pymongoRawQuery': 'pymongoRawQuery'},
      url="https://github.com/YiZhang-You/pymongoRawQuery.git",
      python_requires='>=3.1',
      install_requires=[
          'pymongo>=4.0.1'
      ]
      )
