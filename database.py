import mysql.connector
from config import DB_CONFIG

class Database:
    def __init__(self):
        self.config = DB_CONFIG
        self.connection = None
    
    def connect(self):
        """データベースに接続"""
        try:
            print(f"データベース接続試行: {self.config.get('host')}:{self.config.get('database')}")
            self.connection = mysql.connector.connect(**self.config)
            print("データベース接続成功")
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
            # 接続を確認
            print(f"execute_query 開始")
            if not self.connection or not self.connection.is_connected():
                print("データベース未接続、再接続します")
                self.connect()
            
            print(f"クエリ実行: {query}")
            print(f"パラメータ: {params}")
            
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            print(f"affected rows: {cursor.rowcount}")
            self.connection.commit()
            last_id = cursor.lastrowid
            print(f"lastrowid: {last_id}")
            cursor.close()
            return last_id
        except mysql.connector.Error as err:
            print(f"クエリ実行エラー: {err}")
            print(f"エラーコード: {err.errno}")
            print(f"クエリ: {query}")
            print(f"パラメータ: {params}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"予期しないエラー: {e}")
            return None
    
    def fetch_query(self, query, params=None):
        """クエリを実行（SELECT用）"""
        try:
            # 接続を確認
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return result
        except mysql.connector.Error as err:
            print(f"クエリ取得エラー: {err}")
            print(f"クエリ: {query}")
            print(f"パラメータ: {params}")
            return []
    
    # ユーザー関連のメソッド
    def create_user(self, username):
        """新しいユーザーを作成"""
        try:
            query = "INSERT INTO users (username, display_name) VALUES (%s, %s)"
            user_id = self.execute_query(query, (username, username))
            if user_id:
                print(f"ユーザー作成成功: {username} (ID: {user_id})")
            else:
                print(f"ユーザー作成失敗: {username}")
            return user_id
        except Exception as e:
            print(f"ユーザー作成エラー: {e}")
            return None
    
    def get_user(self, username):
        """ユーザー情報を取得"""
        query = "SELECT * FROM users WHERE username = %s"
        result = self.fetch_query(query, (username,))
        return result[0] if result else None
    
    # メッセージ関連のメソッド
    def save_message(self, user_id, message):
        """メッセージを保存"""
        query = "INSERT INTO messages (user_id, message) VALUES (%s, %s)"
        return self.execute_query(query, (user_id, message))
    
    def get_messages(self, limit=50):
        """最新のメッセージを取得"""
        query = """
              SELECT m.msg_id, m.user_id, u.username, u.display_name, m.message, m.created_at
            FROM messages m
              JOIN users u ON m.user_id = u.user_id
              WHERE m.is_deleted = 0
              ORDER BY m.created_at DESC
            LIMIT %s
        """
        messages = self.fetch_query(query, (limit,))
        return list(reversed(messages))  # 古い順に並び替え
    
    def delete_message(self, msg_id):
        """メッセージを削除（論理削除）"""
        query = "UPDATE messages SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE msg_id = %s"
        return self.execute_query(query, (msg_id,))