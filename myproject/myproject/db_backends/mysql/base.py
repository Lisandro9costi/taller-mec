from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures as BaseFeatures


class DatabaseFeatures(BaseFeatures):
    can_return_rows_from_bulk_insert = False
    can_return_columns_from_insert = False
    minimum_database_version = (10, 4)


class DatabaseWrapper(MySQLDatabaseWrapper):
    features_class = DatabaseFeatures

    def check_database_version_supported(self):
        pass
