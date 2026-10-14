"""A lazy, request-scoped MySQL connection for future search restoration."""

import mysql.connector


class DatabaseConnection:
    def __init__(self, host, port, user, password, database):
        self.settings = dict(host=host, port=port, user=user, password=password, database=database)
        self.connection = None
        self.cursor = None

    def is_connected(self):
        return self.connection is not None and self.connection.is_connected()

    def connect(self):
        if not self.is_connected():
            self.connection = mysql.connector.connect(**self.settings)
            self.cursor = self.connection.cursor(buffered=True, dictionary=True)

    def get_cursor(self):
        self.connect()
        return self.cursor

    def execute(self, query, params=None):
        self.get_cursor().execute(query, params)

    def fetch_all(self):
        return self.cursor.fetchall() if self.cursor is not None else []

    def commit(self):
        if self.is_connected():
            self.connection.commit()

    def handle_unread_result(self):
        # Kept for compatibility. A buffered cursor retains rows for fetch_all.
        pass

    def close(self):
        try:
            if self.cursor is not None:
                self.cursor.close()
        finally:
            self.cursor = None
            try:
                if self.connection is not None:
                    self.connection.close()
            finally:
                self.connection = None
