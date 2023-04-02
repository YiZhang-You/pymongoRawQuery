from urllib import parse

from typing import List
from pymongo import MongoClient

HOST = "localhost"
PORT = 27017


class Connect:

    def __init__(self, host: str, port: int, user: str = None, pwd: str = None, database: str = None):
        self.__host = host
        self.__port = port
        self.__user = user
        self.__pwd = pwd
        self.__database = database
        self.__client = None
        self.__conn_objs = list()
        try:
            self.conn()
        except Exception as e:
            raise ConnectionError(f'mongodb连接异常, 请检查输入信息: {e}')
        finally:
            if len(self.__conn_objs) < 1:
                raise ConnectionError('mongodb连接异常，请检查用户名密码用户权限等信息')

    def conn(self) -> List[object]:
        """ Check the connection to get the connection object """
        _db = False
        if not self.__host:
            self.__host = HOST

        if not self.__host:
            self.__host = PORT

        if self.__pwd:
            self.__pwd = parse.quote(self.__pwd)

        # address port user pwd database
        if self.__database:
            uri = self._splice_uri()
            _db = True
        # address port user pwd
        elif self.__user or self.__pwd:
            uri = self._splice_uri()
        # address port
        else:
            uri = self._splice_uri_simple()

        self.__client = MongoClient(uri, serverSelectionTimeoutMS=5)
        if _db:
            self.__conn_objs.append(self.__client[self.__database])
            return self.__conn_objs

        for item in self.__client.list_database_names():
            self.__conn_objs.append(self.__client[item])

        return self.__conn_objs

    def _splice_uri(self):
        return f'mongodb://{self.__user}:{self.__pwd}@{self.__host}:{self.__port}'

    def _splice_uri_simple(self):
        return f'mongodb://{self.__host}:{self.__port}'

    def get_conn_objs(self):
        return self.__conn_objs

    def close(self):
        """ close connection """
        return self.__client.close()
