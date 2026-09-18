from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mot-chuoi-bi-mat-cua-ban'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ===== DATABASE MODELS =====
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    flashcards = db.relationship('Flashcard', backref='owner', lazy=True)

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(200), nullable=False)
    meaning = db.Column(db.String(200), nullable=False)
    example = db.Column(db.String(500), default='')
    level = db.Column(db.String(50), default='medium')
    learned = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================================
# ĐĂNG KÝ / ĐĂNG NHẬP / ĐĂNG XUẤT
# ============================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Đăng ký thành công! Hãy đăng nhập.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Sai tên đăng nhập hoặc mật khẩu!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ============================================================
# TRANG CHỦ
# ============================================================
@app.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    level = request.args.get('level', 'all')
    page = int(request.args.get('page', 1))
    per_page = 10

    query = Flashcard.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter((Flashcard.word.like(f'%{search}%')) | (Flashcard.meaning.like(f'%{search}%')))
    if level != 'all':
        query = query.filter_by(level=level)

    total = query.count()
    words = query.order_by(Flashcard.id.desc()).offset((page-1)*per_page).limit(per_page).all()

    stats = db.session.query(Flashcard.level, db.func.count(Flashcard.id))\
        .filter(Flashcard.user_id == current_user.id)\
        .group_by(Flashcard.level).all()

    return render_template('index.html',
                           words=words, search=search, level=level,
                           page=page, total=total, per_page=per_page, stats=stats)

# ============================================================
# THÊM / XÓA / SỬA TỪ
# ============================================================
@app.route('/add', methods=['POST'])
@login_required
def add():
    word = request.form['word']
    meaning = request.form['meaning']
    example = request.form.get('example', '')
    level = request.form.get('level', 'medium')
    new_card = Flashcard(word=word, meaning=meaning, example=example, level=level, user_id=current_user.id)
    db.session.add(new_card)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/quick-add', methods=['POST'])
@login_required
def quick_add():
    data = request.form.get('data', '').strip()
    if not data:
        return redirect(url_for('index'))
    for line in data.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = None
        for sep in [' = ', ' =', '= ', '=', '\t', ' - ', ' – ', ': ', '; ', ' | ']:
            if sep in line:
                parts = line.split(sep, 1)
                break
        if not parts:
            parts = line.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[0].strip()
            meaning = parts[1].strip()
            if word and meaning:
                db.session.add(Flashcard(word=word, meaning=meaning, level='medium', user_id=current_user.id))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    card = Flashcard.query.filter_by(id=id, user_id=current_user.id).first()
    if card:
        db.session.delete(card)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update(id):
    card = Flashcard.query.filter_by(id=id, user_id=current_user.id).first()
    if card:
        card.word = request.form['word']
        card.meaning = request.form['meaning']
        card.example = request.form.get('example', '')
        card.level = request.form.get('level', 'medium')
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/reorder', methods=['POST'])
@login_required
def reorder():
    data = request.get_json()
    order = data.get('order', [])
    return jsonify({"success": True})

# ============================================================
# HỌC TỪ
# ============================================================
@app.route('/study')
@login_required
def study():
    word = Flashcard.query.filter_by(user_id=current_user.id, learned=False)\
        .order_by(db.func.random()).first()
    total_words = Flashcard.query.filter_by(user_id=current_user.id).count()
    learned_count = Flashcard.query.filter_by(user_id=current_user.id, learned=True).count()

    message = None
    if word:
        word.learned = True
        db.session.commit()
    else:
        if total_words > 0:
            Flashcard.query.filter_by(user_id=current_user.id).update({'learned': False})
            db.session.commit()
            word = Flashcard.query.filter_by(user_id=current_user.id).order_by(db.func.random()).first()
            if word:
                word.learned = True
                db.session.commit()
            message = "🎉 Chúc mừng! Bạn đã học hết tất cả từ. Bắt đầu vòng mới!"
        else:
            message = "Chưa có từ nào để học. Hãy thêm từ mới!"

    return render_template('study.html', word=word, total_words=total_words,
                           learned_count=learned_count, message=message)

@app.route('/reset-study')
@login_required
def reset_study():
    Flashcard.query.filter_by(user_id=current_user.id).update({'learned': False})
    db.session.commit()
    return redirect(url_for('study'))

# ============================================================
# GAME GHÉP CẶP (ĐÃ SỬA)
# ============================================================
@app.route('/game')
@login_required
def game():
    words = Flashcard.query.filter_by(user_id=current_user.id)\
        .order_by(db.func.random()).limit(10).all()
    
    # Chuyển object thành dict để JSON serializable
    words_data = [{
        'id': w.id,
        'word': w.word,
        'meaning': w.meaning,
        'example': w.example,
        'level': w.level
    } for w in words]
    
    return render_template('game.html', words=words_data)

# ============================================================
# MÁY TÍNH
# ============================================================
@app.route('/calculator')
@login_required
def calculator():
    return render_template('calculator.html')

# ============================================================
# CHẠY APP
# ============================================================
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)