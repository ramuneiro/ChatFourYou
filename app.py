from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from database import Database
from config import SECRET_KEY
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# データベースインスタンス
db = Database()

@app.before_request
def before_request():
    """リクエスト前にデータベースに接続"""
    if not db.connection or not db.connection.is_connected():
        db.connect()

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """ユーザーログイン"""
    data = request.json
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'success': False, 'message': 'ユーザー名を入力してください'})
    
    # ユーザーを取得または作成
    user = db.get_user(username)
    if not user:
        user_id = db.create_user(username)
        if user_id:
            user = {'user_id': user_id, 'username': username}
        else:
            return jsonify({'success': False, 'message': 'ユーザー作成に失敗しました'})
    
    # セッションに保存
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    
    return jsonify({'success': True, 'username': username})

@app.route('/messages', methods=['GET'])
def get_messages():
    """メッセージ一覧を取得"""
    try:
        print("メッセージ取得開始")
        messages = db.get_messages()
        print(f"メッセージ取得成功: {len(messages)}件")
        return jsonify({'messages': messages})
    except Exception as e:
        print(f"メッセージ取得エラー: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'メッセージ取得に失敗しました', 'messages': []}), 500

@app.route('/messages/<int:msg_id>', methods=['DELETE'])
def delete_message(msg_id):
    """メッセージを削除"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'})
    
    result = db.delete_message(msg_id)
    if result is not None:
        # 全クライアントに削除を通知
        socketio.emit('message_deleted', {'msg_id': msg_id}, broadcast=True)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '削除に失敗しました'})

# SocketIOイベントハンドラ
@socketio.on('connect')
def handle_connect():
    """クライアント接続時"""
    print('クライアントが接続しました')

@socketio.on('disconnect')
def handle_disconnect():
    """クライアント切断時"""
    print('クライアントが切断しました')

@socketio.on('send_message')
def handle_message(data):
    """メッセージ送信"""
    if 'user_id' not in session or 'username' not in session:
        emit('error', {'message': 'ログインが必要です'})
        return
    
    message = data.get('message', '').strip()
    if not message:
        emit('error', {'message': 'メッセージが空です'})
        return

    user_id = session['user_id']
    username = session['username']

    # データベースに保存
    msg_id = db.save_message(user_id, message)

    if msg_id:
        # 全クライアントにメッセージをブロードキャスト
        message_data = {
            'msg_id': msg_id,
            'user_id': user_id,
            'username': username,
            'message': message,
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        emit('new_message', message_data, broadcast=True)
    else:
        emit('error', {'message': 'メッセージの送信に失敗しました'})

if __name__ == '__main__':
    # データベースに接続
    if db.connect():
        print("データベースに接続しました")
        # サーバー起動
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    else:
        print("データベース接続に失敗しました")
