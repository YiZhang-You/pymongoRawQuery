# pymongoRawQuery

> 版本：1.0.1
> 
> 
> 作者：益章
> 
> 邮件：yyz18071720400@163.com
> 
> 微信：YiZhang_You
>

# **功能**

## 一、mongodb原生查询

支持mongodb原生语句安全查询数据，拆分校验nosql语句并查询数据（支持find、findOne、sort、limit、skip等一些查询关键字，自动过滤敏感数据库集合以及相应的关键字）

## 二、选择字段、操作、值、值类型以及逻辑符，生成nosql语句并查询数据

支持通过选择字段、操作、值、值类型以及逻辑符，生成nosql语句并查询数据

### 1. 类型于其他连接mongo的筛选工具

![IMG1](https://largestrong-1303013347.cos.ap-nanjing.myqcloud.com/img1.png)

### 2. 支持常用操作符筛选

conditional_operator

```
['$gt', '$gte', '$lt', '$lte', '$eq', '$ne', '$in', '$nin']  # 支持操作符

$gt: 大于
$gte: 大于等于
$lt: 小于
$lte: 小于等于
$eq: 等于
$ne: 不等于
$in: 包含
$nin: 不包含
```

logical_operatory

```
['$and', '$or', ''] 逻辑运算符

$and: 或
$or: 且
```

type

```
['int', 'str', 'date', 'obj_id', 'customize']

int: 整型
str: 字符串
date: 时间
obj_id: bsonId mognoid
customize: 自定义类型
```

## 三、获取mongo数据库结构（支持获取mongo数据库的表、集合以及类型结构）

# 操作示例

### 安装

pip install PyMongoRawQuery

## nosql原生语句查询示例

```python
from pymongoRawQuery import PyMongoRawQuery

# 1. 连接
db = PyMongoRawQuery(host="127.0.0.1", port=27017, user="admin", pwd="admin123", database="test")

# 2. nosql语句
nosql = 'db.getCollection("col").find({"title" : /.*python.*/i})'

# 3. 查询返回接口
for i in db.raw_query(nosql):
    print(i)

"""
{'_id': ObjectId('642592a284000000a5006558'), 'title': 'Python教程', 'description': 'python1', 'by': 'bb', 'url': 'xx', 'tags': ['mongodb', 'database', 'NoSQL'], 'likes': 100.0}
"""
```

## 选择筛选条件查询示例

```python
  """
  conditional_operator: ['$gt', '$gte', '$lt', '$lte', '$eq', '$ne', '$in', '$nin']  # 支持操作符
  logical_operator: ['$and', '$or', '']  # 或与运算
  type: ['int', 'str', 'date', 'obj_id', 'customize']  # 筛选字段类型

	固定格式: 
	[
		{
			"field":"字段名称",
			"conditional_operator":"字段操作",
			"content":"过滤内容",
			"logical_operator":"逻辑操作",
			"type":"content类型"
		}
		...
	]
  """
from pymongoRawQuery import PyMongoRawQuery

# 1. 连接
db = PyMongoRawQuery(host="127.0.0.1", port=27017, user="admin", pwd="admin123", database="test")

# 2. 构建添加过滤参数 
restrictions = [
    {
        "field": "title",  # 查询条件字段
        "conditional_operator": "$in",  # 查询条件字段操作
        "content": "P",  # 查询条件字段值（有大小写区分）
        "logical_operator": "$and",  # 和后面条件的逻辑操作
        "type": "str"  # 查询条件字段值的类型
    },
    {
        "field": "description",  # 查询条件字段
        "conditional_operator": "$nin",  # 查询条件字段操作
        "content": "2",  # 查询条件字段值（有大小写区分）
        "logical_operator": "$and",  # 和后面条件的逻辑操作
        "type": "str"  # 查询条件字段值的类型
    }
]

# 3. 查询并返回数据
print(db.conditional_query(restrictions, 'col'))

"""
[{'_id': ObjectId('642592a284000000a5006558'), 'title': 'Python教程', 'description': 'python1', 'by': 'bb', 'url': 'xx', 'tags': ['mongodb', 'database', 'NoSQL'], 'likes': 100.0}]
"""
```

## 获取mogno数据库结构

```python
from pymongoRawQuery import PyMongoRawQuery

# 1. 连接
db = PyMongoRawQuery(host="127.0.0.1", port=27017, user="admin", pwd="admin123", database="test")

# 2. 查询并返回
print(db.get_table_structure_all())

"""
{'test': {'test': {}, 'col': {'_id': ['bson.objectid.ObjectId'], 'title': ['str'], 'description': ['str'], 'by': ['str'], 'url': ['str'], 'tags': ['list'], 'likes': ['float']}}}
"""
```

