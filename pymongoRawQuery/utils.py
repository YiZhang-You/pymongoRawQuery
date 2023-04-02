class IdentDict(dict):
    """ 处理传递的mongo条件key没有字符串引号的问题 """

    def __missing__(self, key):
        """当字典出错不存在"""
        return key


def mongo_regular_conversion(str_regular: str):
    """mongo正则转换 /^m_/ 转成 '^m_'  """
    str_regular = str(str_regular).strip('"')
    str_regular = str_regular.strip().replace('/', '"')

    if str_regular.count('"') % 2 != 0:
        raise ValueError(f'期望二个/{str_regular}')

    if str_regular.startswith('"'):
        if not str_regular.endswith('"'):
            str_regular = str_regular.replace('"', '')
            return str_regular[:-1], str_regular[-1]
        else:
            str_regular = str_regular.replace('"', '')
            return str_regular, None

    str_regular = str_regular.replace('"', '')
    return str_regular, None
