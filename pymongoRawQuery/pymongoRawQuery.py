from pymongoRawQuery.conn import Connect
from pymongoRawQuery.raw_query import NosqlRawQuery
from pymongoRawQuery.filter_database import FilterDatabase
from pymongoRawQuery.conditional_query import ConditionalQuery


class PyMongoRawQuery:
    """ mongo native query (support find, findOne security
    query, filter some dangerous operations) """

    def __init__(self,
                 host: str,
                 port: int,
                 user: str = None,
                 pwd: str = None,
                 database: str = None
                 ):
        self.database = database
        self.client = Connect(host, port, user, pwd, self.database)
        self.conn_objs = self.client.get_conn_objs()

    def raw_query(self, customize: str) -> list:
        """
        Query and return preview link mongo
        :param customize: nosql statement
        :return: data
        """
        return NosqlRawQuery().get_query(self.conn_objs, customize, self.database)

    def conditional_query(self, constraints_list: list, collection_name: str) -> list:
        """
        Enter the corresponding filter conditions to query data
        :param constraints_list: conditional list
        :param collection_name: query collection name
        :return: data
        """
        return ConditionalQuery().get_query(self.conn_objs, constraints_list, self.database, collection_name)

    def get_table_structure_all(self) -> dict:
        """ get table structure """
        return FilterDatabase().get_table_gather(self.conn_objs)

    def close(self):
        """ close """
        if self.client is not None:
            self.client.close()
