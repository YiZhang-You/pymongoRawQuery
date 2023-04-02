import re
from datetime import datetime

import bson
from bson.errors import InvalidId

from pymongoRawQuery.filter_set import FilterSet
from pymongoRawQuery.verify_nosql import VerifyNosql
from pymongoRawQuery.utils import mongo_regular_conversion
from pymongoRawQuery.filter_database import FilterDatabase
from pymongoRawQuery.exceptions import ParameterErrorFailed, LogicErrorFailed

OPERATOR = ['$gt', '$gte', '$lt', '$lte', '$eq', '$ne', '$in', '$nin']  # 支持操作符
LOGICAL_OPERATOR = ['$and', '$or', '']  # 或与运算
_TYPE = ['int', 'str', 'date', 'obj_id', 'customize']  # 筛选字段类型


class ConditionalQuery(FilterDatabase, VerifyNosql):

    def __init__(self):
        super().__init__()
        self.connection_obj_dict = dict()

    def _verify_database(self, conn_objs: list, database_name: str):
        # 构建一个新的连接对象字典
        for item in conn_objs:
            self.connection_obj_dict[item.name] = {'connection_obj': item,
                                                   'collections_list': item.list_collection_names(session=None)}
        if database_name not in self.connection_obj_dict:
            raise ValueError(f'{database_name} 数据库不存在')

    @staticmethod
    def check_dictionary(constraints_dict):
        """过滤字段为空的字典"""
        if constraints_dict['field'] == '':
            return False
        return True

    def get_query(self, conn_objs: list, constraints_list: list, database_name: str, collection_name: str):
        """
        根据条件获取查询集
        :param collection_name: 查询集合名称
        :param database_name: 查询数据库名称
        :param conn_objs: 连接列表
        :param constraints_list: 筛选条件列表
        :return:
        """
        self._verify_database(conn_objs, database_name)
        constraints_list = list(filter(self.check_dictionary, constraints_list))

        # 查询所有
        if len(constraints_list) == 0:
            query_set = FilterSet(
                self.connection_obj_dict.get(database_name).get('connection_obj')[collection_name]).query_set()
        # 约束条件筛选
        else:
            filters = dict()  # 过滤条件
            _t_list = list()

            information = self.get_table_gather(conn_objs)

            for c_index, item in enumerate(constraints_list):

                field = item.get('field')  # 字段
                conditional_operator = item.get('conditional_operator')  # 操作符
                content = item.get('content')  # 输入内容
                logical_operator = item.get('logical_operator')  # 逻辑操作符
                filter_type = item.get('type')  # 逻辑操作符

                # 校验约束条件信息
                if field not in information[database_name][collection_name]:
                    raise ParameterErrorFailed('集合中没有该字段信息')

                if conditional_operator not in OPERATOR:
                    raise ParameterErrorFailed('条件中出现不允许的操作符')

                if logical_operator not in ['$and', '$or', '']:
                    raise ParameterErrorFailed('条件中出现不允许的操作符')

                if filter_type not in _TYPE:
                    raise ParameterErrorFailed('条件中出现不允许的操作符')

                try:
                    content = self.type_conversion(filter_type, content)
                except Exception as e:
                    raise ParameterErrorFailed(f'筛选条件不符合要求，请检查: {e}')

                if conditional_operator == '$in':
                    try:
                        pattern, options = mongo_regular_conversion(content)
                    except Exception as e:
                        raise LogicErrorFailed(f'筛选条件不符合要求，请检查: {e}')

                    if filter_type in ['obj_id', ]:
                        pattern = str(pattern)

                    if options is None:
                        value = {'$regex': pattern}

                    else:
                        value = {'$regex': pattern, '$options': options}

                elif conditional_operator == '$nin':
                    # value = {'$not': {'$regex': content[0]}}  # mongo4.0版本后
                    # value = {'$not': re.compile(f'{str(pattern)}')}  # mongo4.0版本以前
                    try:
                        pattern, options = mongo_regular_conversion(content)
                    except Exception as e:
                        raise LogicErrorFailed(f'筛选条件不符合要求，请检查：{e}')

                    if filter_type == 'obj_id':
                        pattern = str(pattern)

                    if options is None:
                        value = {'$not': {'$regex': pattern}}
                    else:
                        # value = {'$regex': pattern, '$options': options}
                        value = {'$not': {'$regex': pattern}}


                else:
                    value = {conditional_operator: content}

                # 对应约束条件添加到对应位置
                if len(constraints_list) == 1:
                    filters = {field: value}
                elif len(constraints_list) == 2:
                    if not filters:
                        filters[logical_operator] = _t_list.append({field: value})
                    else:
                        _t_list.append({field: value})
                        filters[constraints_list[0].get('logical_operator')] = _t_list
                else:
                    temporary_list = []
                    # 逻辑运算符是or
                    if logical_operator == '$or':
                        if c_index == 0:  # 表示第一个条件
                            temporary_list.append({field: value})
                            filters['$or'] = temporary_list
                        else:
                            # or 第二个开始后面的条件,
                            # 前面条件是and
                            if constraints_list[c_index - 1].get('logical_operator') == '$and':
                                filters['$and'].append({field: value})
                                temporary_list.append(filters)
                                c_temporary_list = str(temporary_list)
                                eval_temporary_list = eval(c_temporary_list)  # ！ 深拷贝，不能复制正则对象
                                filters['$or'] = eval_temporary_list
                                del filters['$and']
                            else:
                                # 前面条件是or
                                filters['$or'].append({field: value})

                    # 逻辑运算符是and
                    else:
                        if c_index == 0:  # 表示第一个条件
                            temporary_list.append({field: value})
                            filters['$and'] = temporary_list
                        else:
                            # and 第二个开始后面的条件
                            # 前面条件是and
                            if constraints_list[c_index - 1].get('logical_operator') == '$and':
                                if '$or' in filters:
                                    low_list = filters['$or']
                                    for low in low_list[::-1]:
                                        is_break = False
                                        for low_key, low_value in low.items():
                                            if low_key == '$and':
                                                low['$and'].append({field: value})
                                                is_break = True
                                                break
                                        if is_break:
                                            break
                                else:
                                    filters['$and'].append({field: value})
                            else:
                                # 前面条件是or
                                if len(constraints_list) == c_index + 1:  # 如果是最后一个就不用添加and关键字
                                    filters['$or'].append({field: value})
                                else:
                                    temporary_list.append({field: value})
                                    filters['$or'].append({'$and': temporary_list})
            # 查询集
            query_set = FilterSet(self.connection_obj_dict.get(database_name).get('connection_obj')[collection_name],
                                  filters=filters).query_set()

        return query_set

    def type_conversion(self, mg_type, content):
        """根据type校验输入的类型"""

        if mg_type in ['int']:
            try:
                if '.' in str(content):
                    content = float(content)
                else:
                    content = int(content)
            except:
                raise LogicErrorFailed('需要数字类型')

        elif mg_type in ['str']:
            if not isinstance(mg_type, (str,)):
                raise LogicErrorFailed('需要字符串类型')
            if content is None or content == '':
                content = None
            content = content

        elif mg_type in ['date']:
            result_str = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2}) (\d{1,2}):(\d{1,2}):(\d{1,2})', content)
            if result_str is None:
                raise LogicErrorFailed('需要时间类型 年-月-日 时:分:秒')

            year = self.verify_int(result_str.group(1))
            month = self.verify_int(result_str.group(2))
            hour = self.verify_int(result_str.group(3))
            minute = self.verify_int(result_str.group(4))
            second = self.verify_int(result_str.group(5))
            microsecond = self.verify_int(result_str.group(6))
            content = datetime(year, month, hour, minute, second, microsecond)

        elif mg_type in ['obj_id']:
            if not isinstance(mg_type, (str,)):
                raise LogicErrorFailed('需要objId类型')
            try:
                content = bson.ObjectId(content)
            except InvalidId:
                content = str(content)
                # raise LogicErrorFailed('需传递正确的ObjectId')

        elif mg_type in ['customize']:
            if content in ['True', ]:
                content = True
            elif content in ['False', ]:
                content = False
            elif content in ['None', 'Null']:
                content = None
            else:
                content = str(content)

        return content

    @staticmethod
    def verify_int(version):
        """时间类型转成整数"""
        # noinspection PyBroadException
        try:
            version = int(version)
        except:
            version = 1
        return version
