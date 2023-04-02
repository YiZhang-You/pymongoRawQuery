from pymongoRawQuery import PyMongoRawQuery

db = PyMongoRawQuery(host="127.0.0.1", port=27017, user="admin", pwd="admin123", database="test")
nosql = 'db.getCollection("col").find({"title" : /.*python.*/i})'
for i in db.raw_query(nosql):
    print(i)

"""
    OPERATOR = ['$gt', '$gte', '$lt', '$lte', '$eq', '$ne', '$in', '$nin']  # 支持操作符
    LOGICAL_OPERATOR = ['$and', '$or', '']  # 或与运算
    _TYPE = ['int', 'str', 'date', 'obj_id', 'customize']  # 筛选字段类型
"""

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
print(db.conditional_query(restrictions, 'col'))
print(db.get_table_structure_all())
