class FilterSet:
    """ filter query data """

    def __init__(
            self,
            connection_obj: object,
            sort: list = None,
            skip: int = 0,
            limit: int = 0,
            inquiry_mode: str = 'find',
            filters: any = None,
            projection: any = None):
        """
        init
        :param connection_obj: 集合对象
        :param inquiry_mode: 查询方式  find/findOne
        :param filters: 过滤条件
        :param projection: 显示字段 {}
        :param sort: 排序{}
        :param skip: 跳过
        :param limit: 限制数量
        """
        self._connection_obj = connection_obj
        self._sort = sort
        self._skip = skip
        self._limit = limit
        self._inquiry_mode = inquiry_mode
        self._filters = filters
        self._projection = projection

    def query_set(self) -> list:
        if self._sort is None:
            self._sort = list()

        try:
            if self._inquiry_mode == 'find':
                if self._sort:
                    query_set = list(
                        self._connection_obj.find(filter=self._filters, projection=self._projection, skip=self._skip,
                                                  limit=self._limit).sort(self._sort))
                else:
                    query_set = list(
                        self._connection_obj.find(filter=self._filters, projection=self._projection, skip=self._skip,
                                                  limit=self._limit))
            else:
                data_list = list()
                one_data = self._connection_obj.find_one(filter=self._filters, projection=self._projection)
                if one_data is None:
                    query_set = list()
                else:
                    data_list.append(one_data)
                    query_set = data_list

            if len(query_set) < 1:
                query_set = list()
                return query_set

        except Exception as e:
            raise Exception(f'nosql语句编写有误,查询失败：{e}')

        return query_set
