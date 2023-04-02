import re

from pymongo.errors import OperationFailure


class FilterDatabase:

    def __init__(self):
        pass

    @staticmethod
    def _get_keys(db_obj: object, collection: str) -> dict:
        """
        Get all fields and field types in the collection
        :param db_obj:
        :param collection:
        :return:
        """
        result_dict = dict()
        for row in db_obj[collection].find(limit=2):
            for value in row:
                result_dict[value] = list()

                # 得到各个字段的类型(如果同字段名有多种类型，只记录第一条数据的字段类型)
                str_type = str(type(row.get(value)))
                result = re.match(r"<class '(.*?)'>", str_type)
                if result is None:
                    field_type = None
                else:
                    field_type = result.group(1)
                result_dict[value].append(field_type)
        return result_dict

    def get_table_gather(self, conn_objs: list) -> dict:
        """获取数据库中所有的集合以及字段"""
        data = dict()
        try:
            for item in conn_objs:
                database_name = item.name
                # # 过滤数据库
                # if database_name in ['admin', 'config', 'local','test']:
                #     continue
                collection_list = item.list_collection_names()
                data[database_name] = {}
                for collection in collection_list:
                    info = self._get_keys(item, collection)
                    data[database_name][collection] = info
        except OperationFailure:
            raise ConnectionError('mongodb数据库连接异常，请检查用户名密码用户权限等信息')
        except Exception as e:
            raise ConnectionError(f'mongodb数据库连接异常，请检查用户名密码用户权限等信息: {e}')

        return data
