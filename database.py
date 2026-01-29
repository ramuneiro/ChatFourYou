import mysql.connector
from config import DB_CONFIG

class Database:
    def __init__(self):
        self.config = DB_CONFIG
        self.connection = None
    
    def connect(self):
        """データベースに接続"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            return True
        except mysql.connector.Error as err:
            print(f"データベース接続エラー: {err}")
            return False
    
    def disconnect(self):
        """データベース接続を閉じる"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def execute_query(self, query, params=None):
        """クエリを実行（INSERT, UPDATE, DELETE用）"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"クエリ実行エラー: {err}")
            return None
        finally:
            cursor.close()
    
    def fetch_query(self, query, params=None):
        """クエリを実行（SELECT用）"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            return result
        except mysql.connector.Error as err:
            print(f"クエリ取得エラー: {err}")
            return []
        finally:
            cursor.close()
    
    # ユーザー関連のメソッド
    def create_user(self, username):
        """新しいユーザーを作成"""
        query = "INSERT INTO users (username) VALUES (%s)"
        return self.execute_query(query, (username,))
    
    def get_user(self, username):
        """ユーザー情報を取得"""
        query = "SELECT * FROM users WHERE username = %s"
        result = self.fetch_query(query, (username,))
        return result[0] if result else None
    
    # メッセージ関連のメソッド
    def save_message(self, user_id, username, message):
        """メッセージを保存"""
        query = "INSERT INTO messages (user_id, username, message) VALUES (%s, %s, %s)"
        return self.execute_query(query, (user_id, username, message))
    
    def get_messages(self, limit=50):
        """最新のメッセージを取得"""
        query = """
            SELECT id, user_id, username, message, created_at 
            FROM messages 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        messages = self.fetch_query(query, (limit,))
        return list(reversed(messages))  # 古い順に並び替え
    
    def delete_message(self, message_id):
        """メッセージを削除"""
        query = "DELETE FROM messages WHERE id = %s"
        return self.execute_query(query, (message_id,))
