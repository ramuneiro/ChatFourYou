from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from database import Database
from config import SECRET_KEY
import datetime
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MBまで
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

socketio = SocketIO(app, cors_allowed_origins="*")

# データベースインスタンス
db = Database()

@app.before_request
def before_request():
    """リクエスト前にデータベースに接続"""
    try:
        if not db.connection or not db.connection.is_connected():
            db.connect()
    except Exception as e:
        print(f"データベース接続チェックエラー: {e}")
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
    
    # セッションをクリアしてから保存
    session.clear()
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    
    return jsonify({'success': True, 'username': username})

@app.route('/logout', methods=['POST'])
def logout():
    """ユーザーログアウト"""
    session.clear()
    return jsonify({'success': True})

def allowed_file(filename):
    """許可されたファイル拡張子かチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload-image', methods=['POST'])
def upload_image():
    """画像アップロード"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'ファイルがありません'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'ファイルが選択されていません'}), 400
    
    if file and allowed_file(file.filename):
        # ファイル名生成
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # ディレクトリがなければ作成
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # ファイルを保存
        file.save(filepath)
        
        # URLパスを返す
        image_url = f"/static/uploads/{filename}"
        return jsonify({'success': True, 'image_url': image_url})
    
    return jsonify({'success': False, 'message': '無効なファイル形式です（PNG/JPEGのみ）'}), 400

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
    
    # メッセージ情報取得
    message = db.get_message_by_id(msg_id)
    
    # 画像があればファイル削除
    if message and message.get('image_url'):
        image_path = message['image_url'].lstrip('/')
        file_path = os.path.join(os.getcwd(), image_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"画像ファイルを削除しました: {file_path}")
            except Exception as e:
                print(f"画像ファイル削除エラー: {e}")
    
    # データベースから削除
    result = db.delete_message(msg_id)
    if result is not None:
        # 全クライアントに削除通知
        socketio.emit('message_deleted', {'msg_id': msg_id})
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '削除に失敗しました'})


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
    image_url = data.get('image_url', '')
    
    if not message and not image_url:
        emit('error', {'message': 'メッセージまたは画像が必要です'})
        return

    user_id = session['user_id']
    username = session['username']

    # データベースに保存
    msg_id = db.save_message(user_id, message, image_url)

    if msg_id:
        # 全クライアントにメッセージそうしん
        message_data = {
            'msg_id': msg_id,
            'user_id': user_id,
            'username': username,
            'message': message,
            'image_url': image_url,
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
        socketio.run(app, host='0.0.0.0', port=4444, debug=True)
    else:
        print("データベース接続に失敗しました")
