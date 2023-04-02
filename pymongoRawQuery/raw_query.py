import re
import sys
import json
from ast import literal_eval
from json import JSONDecodeError
from collections import namedtuple

from pymongoRawQuery.filter_set import FilterSet
from pymongoRawQuery.verify_nosql import VerifyNosql

from pymongoRawQuery.utils import IdentDict, mongo_regular_conversion

sys.setrecursionlimit(30000)


class NosqlRawQuery(VerifyNosql):
    """ break down nosql """

    def __init__(self):
        super().__init__()
        self._t_dict = None
        self.connection_obj_dict = dict()

    def _verify_database(self, conn_objs: list, database_name: str):
        # 构建一个新的连接对象字典
        for item in conn_objs:
            self.connection_obj_dict[item.name] = {'connection_obj': item,
                                                   'collections_list': item.list_collection_names(session=None)}
        if database_name not in self.connection_obj_dict:
            raise ValueError(f'{database_name} 数据库不存在')

    def get_query(self, conn_objs: list, customize: str, database_name: str) -> any:
        """"""
        self._verify_database(conn_objs, database_name)
        # 校验前半段nosql语句
        customize = re.sub('\\s+', ' ', customize).strip()
        customize = re.sub('%', '', customize).strip()

        if customize.endswith(';'):
            customize = customize[:-1]

        nosql_rule = re.compile(r'^db\.(.*?)\.(findOne|find)[(](.*?)[)]\.')
        check_nosql_forward = nosql_rule.match(customize)
        if check_nosql_forward is None:
            customize = customize + '.'
            check_nosql_forward = nosql_rule.match(customize)
            if check_nosql_forward is None:
                raise ValueError('nosql语句编写有误当前只支持find(),findOne()')
            nosql_index = list(check_nosql_forward.span())  # 前半句nosql长度

        else:
            nosql_index = list(check_nosql_forward.span())  # 前半句nosql长度
            nosql_index[1] = nosql_index[1] - 1

        match_collection_name = check_nosql_forward.group(1)  # 集合名称
        match_inquiry_mode = check_nosql_forward.group(2)  # 查询方式
        match_content = check_nosql_forward.group(3)  # 自定义过滤条件 {},{}
        # 校验前半段nosql提取的信息
        re_name = re.match(r'^getCollection[(](.*?)[)]$', match_collection_name)
        if re_name is None:
            collection_name = match_collection_name
        else:
            collection_name = literal_eval(re_name.group(1))

        filters, projection = self._nosql_injection_verification(match_content)  # query:过滤条件, projection:显示字段

        # 校验后半段nosql语句(sort,skip,limit)
        check_nosql_back = re.findall(r'\.(.*?)[(](.*?)[)]', customize[nosql_index[1]:])
        if match_inquiry_mode == 'findOne':
            if len(check_nosql_back) > 1:
                raise ValueError('findOne不允许添加多余关键字')

        field_dict = dict()  # 关键字构建的字典
        data_length = 0  # 记录数据长度，判断是否有多余字符
        for item in check_nosql_back:
            item_list = [i for i in item if i]
            match_key = item_list[0]  # 关键字
            match_key_len = len(match_key)
            # noinspection PyBroadException
            try:
                match_value = item_list[1]  # 关键字中的内容
                match_value_len = len(match_value)
            except:
                match_value_len = 0
                match_value = None

            data_length += match_key_len + match_value_len + 3  # 记录长度 +3 . ( )

            # 校验关键字类型参数
            if match_key in ['sort', 'skip', 'limit']:
                if match_key in ['skip', 'limit']:
                    try:
                        if match_value is None:
                            match_value = 0
                        match_value = int(match_value)
                    except:
                        raise ValueError('nosql语句编写有误,skip、limit需要传递整数')
                else:
                    try:
                        match_value = eval(match_value, IdentDict())
                        # match_value = literal_eval(
                        #     match_value.replace('null', 'None').replace('true', 'True').replace('false', 'False'))
                        if not isinstance(match_value, dict):
                            raise ValueError('nosql语句编写有误,需要对象{}')
                    except:
                        raise ValueError('nosql语句编写有误,sort需要字典类型')

                if field_dict.get(match_key) is None:
                    field_dict[match_key] = match_value
                else:
                    raise ValueError('nosql语句编写有误,有重复关键字')

            else:
                raise ValueError('nosql语句编写有误,只支持sort,skip,limit')

        # 判断是否有多余字符
        if len(customize[nosql_index[1]:]) != data_length:
            raise ValueError('nosql语句编写有误,有多余字符')

        skip = 0
        limit = 0
        sort_list = list()
        if 'sort' in field_dict:
            for key, value in field_dict.get('sort').items():
                sort_list.append((key, value))
        if 'limit' in field_dict:
            limit = field_dict.get('limit')
        if 'skip' in field_dict:
            skip = field_dict.get('skip')

        if not filters:
            filters = None
        if not projection:
            projection = None

        try:
            query_set = FilterSet(
                self.connection_obj_dict.get(database_name).get('connection_obj')[collection_name],
                filters=filters,
                projection=projection,
                skip=skip,
                limit=limit,
                sort=sort_list,
                inquiry_mode=match_inquiry_mode
            ).query_set()

        except Exception:
            raise ValueError('nosql语句编写有误,查询失败')

        return query_set

    def _nosql_injection_verification(self, match_content):
        """校验nosql中的条件"""
        # 校验类型是不是字典
        try:
            match_content = match_content.strip()
            if len(match_content) == 0:
                match_content = '{}'

            # 替换时间类型
            match_content = match_content.replace("ISODate", "parser.parse")

            try:
                query_dict = self._mongo_query_loads(match_content)
            except Exception as e:
                raise ValueError(f'nosql语句编写有误: {e}')

            # null = None
            # true = True
            # false = False
            # query_dict = eval(match_content.replace('/', ''))
            Subscriber = namedtuple('Subscriber', ['query', 'projection'])
            try:
                query = query_dict[0]  # 约束条件
            except:
                query = dict()
            try:
                projection = query_dict[1]  # 筛选字段
            except:
                projection = dict()

            sub = Subscriber(query, projection)
            if not isinstance(sub.query, dict):
                raise ValueError('error:nosql语句条件编写有误,需要传递{\'key\':value}或{key:value}形式')
            if not isinstance(sub.projection, dict):
                raise ValueError('error:nosql语句条件编写有误,需要传递{\'key\':value}或{key:value}形式')

        except Exception as e:
            raise ValueError('error:nosql语句条件编写有误,需要传递{\'key\':value}或{key:value}形式')

        # 校验查询条件
        if sub.query:
            keys, values = self.get_dict_key_value(sub.query)
            danger = {'$where', '$accumulator', '$function'} & set(keys)  # 不允许关键字集合
            if len(danger) != 0:
                keys.clear()
                values.clear()
                raise ValueError(f'error:nosql语句条件编写有误,不允许使用关键字：{danger}')

        # 校验显示字段
        if sub.projection:
            pass

        return sub.query, sub.projection

    def _mongo_query_loads(self, string):
        """
        将给定的mongo字符串转成字典
        :param string: find、find0ne 括号中的查询集
        :return:
        """
        string = string.replace("ISODate", "parser.parse")

        string = self._dictionary_quote_handling(string)  # 得到替换好的新字符串

        stack = list()  # 记录每个字符
        mongo_stack = list()  # 记录带有bson类型的字典
        mongo_stack2 = list()  # 临时存放mongo
        temporary_record_id = 0  # 临时记录id
        for element in string:
            if element in {'}', }:
                reverse_stack = stack[::-1]  # 反转列表找相反的括号 123456 654321
                try:
                    z_index = reverse_stack.index('{')  # 最近{的下标
                except ValueError:
                    raise ValueError('期望得到{')

                str_dict = None
                try:
                    str_dict = ''.join(stack[len(reverse_stack) - z_index - 1:]) + '}'  # 碰到}，向前面查找{,然后元素进行切分转成字典
                    convert_dict = json.loads(str_dict, object_pairs_hook=self.same_key)  # 相同的key合并成一个in语句

                except:
                    # 处理字符串{}中的正则类型、mongo类型
                    convert_dict = dict()  # 手动构建的字典

                    key_value_list = self._extract_key_value(str_dict)  # 提取字典中所有的key,value

                    convert_dict = self._error_statement_conversion(key_value_list, mongo_stack, mongo_stack2,
                                                                    temporary_record_id, convert_dict)  # 处理mongo和正则类型
                del stack[len(reverse_stack) - z_index - 1:]  # 删除拼接好字典的字符串下标

                stack.append(json.dumps(convert_dict))  # 将字典重新添加到列表中

            else:
                stack.append(element)
            temporary_record_id = temporary_record_id + 1

        #  删除掉列表中的,号， 也是Mongo筛选语句的分隔符
        now_stack = list()
        for item in stack:
            if item in [',', ' ', '']:
                continue
            try:
                now_stack.append(json.loads(item, object_pairs_hook=self.same_key))
            except JSONDecodeError:
                raise Exception(f'期望一个字典类型: {item}')
        stack.clear()

        # 最后需要把mongo的类型替换回来
        for item in mongo_stack2:
            key1 = item[0]
            reality_value = item[1]
            temporary_id = item[2]
            for row in mongo_stack:

                def replace_value(recently_dict: dict, dict_key, dict_value, temp_id):
                    """将mongo的value替换回来"""
                    for recently_key, recently_value in recently_dict.items():
                        try:
                            if recently_key == temp_id or str(recently_value) == str(dict_key):
                                if isinstance(recently_value, (dict,)):
                                    return self.replace_value(recently_dict[recently_key], dict_key, dict_value,
                                                              temp_id)

                                else:
                                    if recently_value == temp_id:
                                        recently_dict[dict_key] = eval(dict_value)

                        except TypeError as a:
                            return

                replace_value(row, key1, reality_value, temporary_id)

        if len(mongo_stack) > 0:
            now_stack = self.data_process(now_stack, mongo_stack)

        return now_stack

    def _error_statement_conversion(self, key_value_list, mongo_stack, mongo_stack2, temporary_record_id, convert_dict):
        """
        正则mongo语句转换，将报错的语句通过一个临时id替换掉
        :param key_value_list: 所有的key,value
        :param mongo_stack: 临时存放字典的列表
        :param mongo_stack2: 临时mongo列表
        :param temporary_record_id: 临时id
        :param convert_dict: 字典
        :return:
        """

        nested_key = list()
        for index, key_value in enumerate(key_value_list):  # 考虑嵌套字典的情况
            key_dict_str = key_value[0]
            value_dict_str = key_value[1]
            if key_dict_str in ['', ]:
                raise ValueError(f'期望得到一个关键字: {key_dict_str}')

            # 处理嵌套的字典类型('b', '{')
            try:
                b = isinstance(int(key_dict_str), int) and value_dict_str == '""'
                key_dict_str = int(key_dict_str)
            except:
                b = False

            if str(value_dict_str).strip() in ['{', ] or b:
                try:
                    # if not b:
                    if len(key_value_list) != index + 1:
                        _ = key_value_list[index + 1]
                        nested_key.append(key_dict_str)

                except IndexError:
                    raise ValueError(f'请传递正确的字典:{key_dict_str}:{value_dict_str}')
                if len(key_value_list) != index + 1:
                    continue

            # 处理字典 value 中引号的问题
            if isinstance(value_dict_str, str):
                if '"' in value_dict_str or "'" in value_dict_str:
                    if value_dict_str.count('"') % 2 != 0 or value_dict_str.count("'") % 2 != 0:
                        raise ValueError(f'期望字典value被引号包围，而不是只有一个引号: {value_dict_str}')

            # 一、处理正则
            try:
                if value_dict_str.strip() in ['true']:
                    value_dict_str = True
                if value_dict_str.strip() in ['false']:
                    value_dict_str = False
                if value_dict_str.strip() in ['null', 'Null']:
                    value_dict_str = None
                int_type = isinstance(int(value_dict_str), (int, float))
            except:
                int_type = False

            if not isinstance(value_dict_str, str):
                pass

            elif key_dict_str in ['$regex', '$in', '$nin'] or value_dict_str.startswith('/'):

                # a.如果key是正则的参数$regex（value：正则，value：字符串）
                if key_dict_str == '$regex':

                    # 如果value是字符串正则类型
                    if value_dict_str.startswith('"') or value_dict_str.startswith("'"):
                        if key_dict_str not in convert_dict:
                            convert_dict.update(
                                {'$in': [re.compile(str(value_dict_str).replace('"', '').replace("'", ''))]})
                        else:
                            convert_dict['$in'].append(
                                re.compile(str(value_dict_str).replace('"', '').replace("'", '')))

                    # 如果value是正则类型
                    elif value_dict_str.startswith('/'):
                        pattern, options = mongo_regular_conversion(value_dict_str)
                        if options is None:
                            if key_dict_str not in convert_dict:
                                convert_dict.update({'$in': [re.compile(str(pattern))]})
                                # if '$in' not in convert_dict:  # mongo中会抵消掉前面的正则
                                #     convert_dict.update({'$in': [re.compile(str(pattern))]})
                                # else:
                                #     convert_dict['$in'].append(re.compile(str(pattern)))

                            else:
                                convert_dict['$in'].append(re.compile(str(pattern)))

                        else:
                            if key_dict_str not in convert_dict:
                                if str(options).strip() == 'i':
                                    convert_dict.update({'$in': [re.compile(str(pattern), re.IGNORECASE)]})
                                elif str(options).strip() == 'm':
                                    convert_dict.update({'$in': [re.compile(str(pattern), re.MULTILINE)]})
                                elif str(options).strip() == 'x':
                                    convert_dict.update({'$in': [re.compile(str(pattern), re.VERBOSE)]})
                                elif str(options).strip() == 's':
                                    convert_dict.update({'$in': [re.compile(str(pattern), re.DOTALL)]})
                                else:
                                    convert_dict.update({'$in': [re.compile(str(pattern))]})
                            else:
                                if str(options).strip() == 'i':
                                    convert_dict['$in'].append(re.compile(str(pattern), re.IGNORECASE))
                                elif str(options).strip() == 'm':
                                    convert_dict['$in'].append(re.compile(str(pattern), re.MULTILINE))
                                elif str(options).strip() == 'x':
                                    convert_dict['$in'].append(re.compile(str(pattern), re.VERBOSE))
                                elif str(options).strip() == 's':
                                    convert_dict['$in'].append(re.compile(str(pattern), re.DOTALL))
                                else:
                                    convert_dict['$in'].append(re.compile(str(pattern)))
                    else:
                        raise ValueError(f'期望正则表达式用/开头: {value_dict_str}')

                # b. 开头为`/`统一处理成正则（value是已/开头）
                elif value_dict_str.startswith('/'):

                    pattern, options = mongo_regular_conversion(value_dict_str)
                    if options is None:
                        if '$in' in convert_dict:
                            convert_dict['$in'].append(re.compile(str(pattern)))
                        else:
                            convert_dict.update({key_dict_str: {'$regex': str(pattern)}})
                    else:
                        convert_dict.update({key_dict_str: {'$regex': str(pattern), '$options': options}})
                # c. 如果key是$in、$nin value列表中是正则
                elif key_dict_str == '$in' or key_dict_str == '$nin':
                    value_dict_str = value_dict_str.strip()
                    if not value_dict_str.startswith('[') or not value_dict_str.endswith(']'):
                        raise Exception('关键字in nin 需要传递[]类型', value_dict_str)

                    in_nin_list = list()  # 存放in nin中值的列表
                    for item in value_dict_str.strip('[]').split(','):
                        item_b = item.strip()

                        if '"' in item_b or "'" in item_b:
                            if item_b.count('"') % 2 != 0 or item_b.count("'") % 2 != 0:
                                raise Exception(f'期望字符串被引号包围，而不是只有一个引号：{item}')
                            else:
                                in_nin_list.append(item.replace('"', '').replace("'", ''))
                            continue
                        else:
                            pattern, options = mongo_regular_conversion(item_b)  # 正则处理

                        if options is None:
                            in_nin_list.append(re.compile(str(pattern)))
                        else:
                            if str(options).strip() == 'i':
                                in_nin_list.append(re.compile(str(pattern), re.IGNORECASE))
                            elif str(options).strip() == 'm':
                                in_nin_list.append(re.compile(str(pattern), re.MULTILINE))
                            elif str(options).strip() == 'x':
                                in_nin_list.append(re.compile(str(pattern), re.VERBOSE))
                            elif str(options).strip() == 's':
                                in_nin_list.append(re.compile(str(pattern), re.DOTALL))
                            else:
                                in_nin_list.append(re.compile(str(pattern)))

                    if key_dict_str not in convert_dict:
                        convert_dict.update({key_dict_str: in_nin_list})
                    else:
                        convert_dict[key_dict_str].append(in_nin_list)

            # 二、报错字典中的正常类型(字符串，数字，布尔，null)
            elif value_dict_str.startswith('"') or value_dict_str.startswith("'") or int_type or value_dict_str in [
                True, False, None]:
                if isinstance(value_dict_str, (str,)):
                    value_dict_str = str(value_dict_str).replace('"', '').replace("'", '')

                if key_dict_str not in convert_dict:
                    convert_dict[key_dict_str] = value_dict_str
                else:
                    convert_dict[key_dict_str] = value_dict_str

            # 三、mongo类型错误
            else:

                if key_dict_str not in convert_dict:
                    convert_dict[key_dict_str] = temporary_record_id
                else:
                    convert_dict[key_dict_str]['$in'].append({key_dict_str: temporary_record_id})

                # 添加一个临时标识，后面通过这个临时标识去寻找对应的key,value
                mongo_stack2.append((key_dict_str, value_dict_str, temporary_record_id))  # 记录转换出错的类型（key,value,临时标识）

            # 四、替换临时id
            if len(nested_key) == 0:
                mongo_stack.append({temporary_record_id: convert_dict})
            else:
                nested_dict = dict()
                nested_state = False
                for item in nested_key:  # 判断前面字典是嵌套类型还是单独类型
                    if isinstance(item, (int,)):
                        nested_state = True
                        break

                # 前面是一个单独的字典
                if nested_state:
                    for n_value in nested_key:
                        if len(nested_dict) == 0:
                            nested_dict[n_value] = None
                        else:
                            key, = list(nested_dict.keys())[0]
                            nested_dict[key] = {n_value: '""'}

                    convert_dict.update(nested_dict)
                    mongo_stack.append({temporary_record_id: convert_dict})
                    nested_dict.clear()
                # 是一个嵌套字典
                else:

                    for n_value in nested_key:
                        if len(nested_dict) == 0:
                            nested_dict[n_value] = None
                        else:
                            (key, value), = nested_dict.items()
                            nested_dict[key] = {n_value: None}

                    if isinstance(key_dict_str, (int,)):
                        if key_dict_str in convert_dict:
                            del convert_dict[key_dict_str]

                        def inner_dict(nested_dict):
                            (key, value), = nested_dict.items()
                            if isinstance(value, dict):
                                inner_dict(value)
                            else:
                                nested_dict[key] = {key_dict_str: ''}
                            return nested_dict

                        nested_dict = inner_dict(nested_dict)
                        convert_dict.update(nested_dict)
                        mongo_stack.append({temporary_record_id: convert_dict})
                        nested_dict.clear()
                    else:

                        def inner_dict(nested_dict):
                            (key, value), = nested_dict.items()
                            if isinstance(value, dict):
                                inner_dict(value)
                            else:
                                # nested_dict[key] = {key_dict_str: ''}
                                nested_dict[key] = {key_dict_str: value_dict_str}
                            return nested_dict

                        nested_dict = inner_dict(nested_dict)
                        try:
                            del convert_dict[key_dict_str]
                        except:
                            pass

                        convert_dict.update(nested_dict)  # 先用临时的标识代替
                        mongo_stack.append({temporary_record_id: convert_dict})

                        nested_dict.clear()

        return {temporary_record_id: ''}

    @staticmethod
    def same_key(string):
        """解决字典中保留相同的key,有相同的语句直接变成一个in语句"""
        result = dict()
        count = dict()
        for key, val in string:
            if key in count:
                count[key] = 1 + count[key]
            else:
                count[key] = 1
            if key in result:
                if count[key] > 2:
                    result[key].append(val)
                else:
                    result[key] = {"$in": [result[key], val]}
            else:
                result[key] = val
        return result

    @staticmethod
    def _dictionary_quote_handling(string):
        """
        将key全部变成双引号
        :param string: find、find0ne 括号中的查询集
        :return:
        """
        # 1、提取所有的key
        string2 = re.sub(r"\(.*?\)", "", string)
        string2 = string2.replace(' ', '')

        re_dict_key_list = re.findall('(.*?):', string2)  # 得到所有的key（需要进行精细处理）

        for index, value in enumerate(re_dict_key_list):
            value = str(value).strip().replace('{', '').replace('}', '')
            if ',' in value:
                re_dict_key_list[index] = value.split(',')[-1]
            else:
                re_dict_key_list[index] = value

        # 2、替换key,统一引号
        # string = string.replace(' ', '')
        replace_str_list = list()  # 替换的字符串列表
        match_content_list = list(string)  # 字符串变成列表
        for row, item in enumerate(re_dict_key_list):
            # 处理字典 key 中引号问题
            if '"' in item or "'" in item:
                if item.count('"') % 2 != 0 or item.count("'") % 2 != 0:
                    raise IndexError(f'期望字典key被引号包围，而不是只有一个引号: {item}')

            replace_str = ''.join(match_content_list)
            if item.find("'") != -1 or item.find('"') != -1:  # 引号统一处理都变成双引号
                replace_str = replace_str.replace('"', "'").replace("'", '"')
                now_match_content = replace_str.replace(f"{item}", f"{item}", 1)
            else:
                now_match_content = replace_str.replace(f"{item}", f'"{item}"', 1)

            index = replace_str.find(item) + len(item) + 1  # key所在的下标
            replace_str_list.append(now_match_content[0:index])  # 把替换好的字符串切片到replace_str_list
            if len(re_dict_key_list) == row + 1:  # 如果是最后一部分
                replace_str_list.append(now_match_content[index:])
            match_content_list = list(now_match_content[index:])  # 将切片后剩余的部分重新给到match_content_list中

        return ''.join(replace_str_list)

    @staticmethod
    def _extract_key_value(str_dict):
        """校验并提取字符中字典的key，value"""

        str_dict = str_dict.strip('{}')
        str_dict2 = re.sub(r"\(.*?\)", "", str_dict)

        re_find_list = re.findall('(.*?):', str_dict2)
        # 替换字符串，考虑一个字典有多个元素的情况
        for index, value in enumerate(re_find_list):
            value = str(value).strip()
            if ',' in value:
                re_find_list[index] = value.split(',')[-1].replace('{', '').replace('[', '').replace('(', '')
            else:
                re_find_list[index] = value.replace('{', '').replace('[', '').replace('(', '')

        keys_values_list = list()  # 存放关键字key,value
        # 根据key的下标取value的值
        for index, value in enumerate(re_find_list):
            if len(re_find_list) == index + 1:
                item_index = str_dict.find(re_find_list[index],
                                           sum([len(item[0]) + len(item[1]) + 2 for item in keys_values_list])) + len(
                    re_find_list[index])
                item_index_next = None
            else:
                if len(keys_values_list) == 0:
                    item_index = str_dict.find(re_find_list[index]) + len(re_find_list[index])
                    item_index_next = str_dict.find(re_find_list[index + 1], item_index)
                else:
                    item_index = str_dict.find(re_find_list[index],
                                               sum([len(item[0]) + len(item[1]) + 2 for item in
                                                    keys_values_list])) + len(
                        re_find_list[index])
                    item_index_next = str_dict.find(re_find_list[index + 1], item_index)

            if item_index_next is None:
                value = str_dict[item_index:]
            else:
                value = str_dict[item_index:item_index_next]

            if len(value) > 1:
                value = value.strip()
                if value.startswith(':'):
                    value = value[1:].strip()
                    value = ':' + value

            if value in [':', '']:
                raise ValueError('请传递正确字典类型:', str_dict)

            if value == '{':  # 考虑嵌套字典的情况
                pass
            else:
                if value.endswith(','):  # 剔除掉多余字符
                    value = value[1:-1]
                else:
                    value = value[1:]

            key = re_find_list[index].strip().replace('"', '')
            value = value.strip().replace('}', '')
            try:
                value1 = literal_eval(value)
                if isinstance(value1, (int, float)):
                    value = value1
                else:
                    value = value
            except:
                pass
            keys_values_list.append((key, value))
        return keys_values_list

    def inner(self, item_key, bb):
        if self._t_dict is None:
            self._t_dict = dict()

        for item_b in bb:
            (keys_id,) = item_b.keys()
            try:
                if int(keys_id) == int(item_key):
                    (values,) = item_b.values()

                    if len(self._t_dict) == 0:
                        self._t_dict.update(values)
                        break
                    else:
                        self._t_dict.update(values)
                        del self._t_dict[str(keys_id)]
                        break
            except:
                pass

        keys_list, _ = self.get_dict_key_value(self._t_dict)
        for item_b in bb:
            (keys_id,) = item_b.keys()
            if str(keys_id) in keys_list:
                self.inner(str(keys_id), bb)
            else:
                return self._t_dict

    def data_process(self, cc, bb):
        """得到处理好的字典"""
        for item in cc:
            for item_key, item_value in list(item.items()):
                try:
                    isinstance(int(item_key), int)
                    inner_dict = self.inner(item_key, bb)
                    item.update(inner_dict)
                    del item[item_key]
                    keys_list, _ = self.get_dict_key_value(inner_dict)
                    for key in keys_list:
                        if isinstance(key, int):
                            self.data_process([item], bb)
                except:
                    if isinstance(item_value, dict):
                        self.data_process([item_value], bb)
                    if isinstance(item_value, list):
                        for row in item_value:
                            self.data_process([row], bb)
            self._t_dict.clear()
        return cc

    def get_dict_key_value(self, in_dict, keys=None, values=None):
        """ 获取所有的 key, value """
        if values is None:
            values = list()
        if keys is None:
            keys = list()
        for key, value in in_dict.items():
            keys.append(key)
            if isinstance(value, dict):
                self.get_dict_key_value(value, keys, values)
            else:
                values.append(value)
        return keys, values

    def replace_value(self, recently_dict: dict, dict_key, dict_value, temporary_id):
        """将mongo的value替换回来"""
        recently_key, recently_value = None, None
        try:
            for recently_key, recently_value in recently_dict.items():
                try:
                    if str(recently_key) == str(dict_key):
                        if isinstance(recently_value, int):
                            if int(recently_value) == int(temporary_id):
                                recently_dict[recently_key] = eval(dict_value)
                                return
                except TypeError as a:
                    return
        except AttributeError:
            pass
        return self.replace_value(recently_dict[recently_key], dict_key, dict_value, temporary_id)
