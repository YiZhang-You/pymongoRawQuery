from distutils.core import setup
import setuptools

packages = ['pymongoRawQuery']  # 唯一的包名，自己取名
setup(
      name='pymongoRawQuery',
      version='1.0.0',
      description='支持mongodb原生语句安全查询数据，拆分校验nosql语句并查询数据（支持find、findOne、sort、limit、skip等一些查询关键字，自动过滤敏感数据库集合以及相应的关键字）',
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
