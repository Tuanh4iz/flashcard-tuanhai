


from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3

app = Flask(__name__)

# ============================================================
# HÀM KẾT NỐI DATABASE
# ============================================================
def get_db():
    conn = sqlite3.connect('database.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        meaning TEXT NOT NULL,
        example TEXT,
        level TEXT DEFAULT 'medium'
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS study_session (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word_id INTEGER UNIQUE,
        learned INTEGER DEFAULT 0
    )''')
    try:
        conn.execute('SELECT level FROM words LIMIT 1')
    except sqlite3.OperationalError:
        conn.execute('ALTER TABLE words ADD COLUMN level TEXT DEFAULT "medium"')
        conn.commit()
    return conn

# ============================================================
# TRANG CHỦ
# ============================================================
@app.route('/')
def index():
    search = request.args.get('search', '')
    level = request.args.get('level', 'all')
    page = int(request.args.get('page', 1))
    per_page = 10

    conn = get_db()
    query = 'SELECT * FROM words WHERE 1=1'
    params = []
    if search:
        query += ' AND (word LIKE ? OR meaning LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    if level != 'all':
        query += ' AND level = ?'
        params.append(level)
    
    count_query = query.replace('*', 'COUNT(*)')
    total = conn.execute(count_query, params).fetchone()[0]
    
    offset = (page - 1) * per_page
    query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    words = conn.execute(query, params).fetchall()
    
    stats = conn.execute('SELECT level, COUNT(*) FROM words GROUP BY level').fetchall()
    conn.close()
    
    return render_template('index.html', 
                         words=words,
                         search=search,
                         level=level,
                         page=page,
                         total=total,
                         per_page=per_page,
                         stats=stats)

# ============================================================
# THÊM TỪ
# ============================================================
@app.route('/add', methods=['POST'])
def add():
    word = request.form['word']
    meaning = request.form['meaning']
    example = request.form.get('example', '')
    level = request.form.get('level', 'medium')
    conn = get_db()
    conn.execute('INSERT INTO words (word, meaning, example, level) VALUES (?, ?, ?, ?)',
                 (word, meaning, example, level))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ============================================================
# THÊM NHANH
# ============================================================
@app.route('/quick-add', methods=['POST'])
def quick_add():
    data = request.form.get('data', '').strip()
    if not data:
        return redirect(url_for('index'))
    
    conn = get_db()
    lines = data.split('\n')
    added = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = None
        separators = [' = ', ' =', '= ', '=', '\t', ' - ', ' – ', ': ', '; ', ' | ']
        for sep in separators:
            if sep in line:
                parts = line.split(sep, 1)
                break
        if not parts:
            parts = line.split(maxsplit=1)
        if len(parts) == 2:
            word = parts[0].strip()
            meaning = parts[1].strip()
            if word and meaning:
                conn.execute('INSERT INTO words (word, meaning, level) VALUES (?, ?, ?)',
                             (word, meaning, 'medium'))
                added += 1
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ============================================================
# XÓA TỪ
# ============================================================
@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db()
    conn.execute('DELETE FROM words WHERE id = ?', (id,))
    conn.execute('DELETE FROM study_session WHERE word_id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ============================================================
# SỬA TỪ
# ============================================================
@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    word = request.form['word']
    meaning = request.form['meaning']
    example = request.form.get('example', '')
    level = request.form.get('level', 'medium')
    conn = get_db()
    conn.execute('UPDATE words SET word=?, meaning=?, example=?, level=? WHERE id=?',
                 (word, meaning, example, level, id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ============================================================
# SẮP XẾP LẠI (KÉO THẢ)
# ============================================================
@app.route('/reorder', methods=['POST'])
def reorder():
    data = request.get_json()
    order = data.get('order', [])
    # Lưu thứ tự (có thể thêm cột `position` vào database nếu cần)
    return jsonify({"success": True})

# ============================================================
# HỌC TỪ
# ============================================================
@app.route('/study')
def study():
    conn = get_db()
    row = conn.execute('''
        SELECT w.* FROM words w
        LEFT JOIN study_session s ON w.id = s.word_id
        WHERE s.learned IS NULL OR s.learned = 0
        ORDER BY RANDOM() LIMIT 1
    ''').fetchone()
    
    total_words = conn.execute('SELECT COUNT(*) FROM words').fetchone()[0]
    learned_count = conn.execute('SELECT COUNT(*) FROM study_session WHERE learned = 1').fetchone()[0]
    
    if row:
        conn.execute('INSERT OR IGNORE INTO study_session (word_id, learned) VALUES (?, 0)', (row[0],))
        conn.execute('UPDATE study_session SET learned = 1 WHERE word_id = ?', (row[0],))
        conn.commit()
        word = row
        message = None
    else:
        if total_words > 0:
            conn.execute('DELETE FROM study_session')
            conn.commit()
            word = conn.execute('SELECT * FROM words ORDER BY RANDOM() LIMIT 1').fetchone()
            if word:
                conn.execute('INSERT INTO study_session (word_id, learned) VALUES (?, 1)', (word[0],))
                conn.commit()
            message = "🎉 Chúc mừng! Bạn đã học hết tất cả từ. Bắt đầu vòng mới!"
        else:
            word = None
            message = "Chưa có từ nào để học. Hãy thêm từ mới!"
    
    conn.close()
    return render_template('study.html', 
                         word=word, 
                         total_words=total_words, 
                         learned_count=learned_count,
                         message=message)

# ============================================================
# RESET HỌC
# ============================================================
@app.route('/reset-study')
def reset_study():
    conn = get_db()
    conn.execute('DELETE FROM study_session')
    conn.commit()
    conn.close()
    return redirect(url_for('study'))

# ============================================================
# GAME GHÉP CẶP
# ============================================================
@app.route('/game')
def game():
    conn = get_db()
    words = conn.execute('SELECT * FROM words ORDER BY RANDOM() LIMIT 10').fetchall()
    conn.close()
    return render_template('game.html', words=words)

# ============================================================
# MÁY TÍNH
# ============================================================
@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

# ============================================================
# CHẠY APP
# ============================================================
if __name__ == '__main__':
    app.run(debug=True)