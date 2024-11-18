from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from config import Config
import openai  # 追加

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# OpenAI APIキーの設定（追加）
openai.api_key = app.config.get('OPENAI_API_KEY')

# モデル定義
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'teacher'
    full_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(20), unique=True)  # 学生の場合
    department = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # プロフィール情報
    profile_photo = db.Column(db.String(255))  # 写真のファイルパス
    desired_job = db.Column(db.String(100))    # 希望職種
    current_goal = db.Column(db.Text)          # 現在の目標
    skills_and_interests = db.Column(db.Text)  # スキルと興味
    self_introduction = db.Column(db.Text)     # 自己紹介
    github_url = db.Column(db.String(255))     # GitHubリンク
    portfolio_url = db.Column(db.String(255))  # ポートフォリオサイトリンク
    grade = db.Column(db.String(20))           # 学年

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        return self.role == 'student'

    def is_teacher(self):
        return self.role == 'teacher'

class LearningRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    learning_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date) 
    location = db.Column(db.String(200))  
    achievement = db.Column(db.Text)
    reflection = db.Column(db.Text)  
    skills = db.Column(db.String(500))  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 教員のフィードバック
    feedback = db.Column(db.Text)
    feedback_teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    feedback_date = db.Column(db.DateTime)

    student = db.relationship('User', foreign_keys=[student_id], backref='records')
    feedback_teacher = db.relationship('User', foreign_keys=[feedback_teacher_id])

class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('learning_record.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    record = db.relationship('LearningRecord', backref='attachments')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# GPT関連の関数（追加）
def format_student_profile(student):
    """学生のプロフィール情報をGPT用に整形"""
    profile_items = []
    
    if student.department:
        profile_items.append(f"専攻: {student.department}")
    if student.grade:
        profile_items.append(f"学年: {student.grade}")
    if student.desired_job:
        profile_items.append(f"希望職種: {student.desired_job}")
    if student.current_goal:
        profile_items.append(f"目標: {student.current_goal}")
    if student.skills_and_interests:
        profile_items.append(f"スキルと興味: {student.skills_and_interests}")
    if student.self_introduction:
        profile_items.append(f"自己紹介: {student.self_introduction}")
        
    return "\n".join(profile_items)

def analyze_student_match(query, student_profile):
    """GPTを使用して学生とクエリのマッチング分析を行う"""
    try:
        # APIキーをConfigから取得してクライアントを初期化
        client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": """
                あなたは学生のプロフィールと求める人材要件を比較し、
                マッチ度を評価する専門家です。以下の点を分析してください：
                - スキルの一致度
                - 経験や学習内容の関連性
                - 意欲や目標の方向性
                - 求める人材像との総合的な適合性
                
                回答は以下の3つの要素を含むJSONとしてください：
                1. マッチング理由の説明（100-200文字）
                2. 関連するスキルや強みのリスト（3-5個）
                3. マッチ度スコア（0-100の整数）
                """},
                {"role": "user", "content": f"""
                求める人材要件:
                {query}

                学生のプロフィール:
                {student_profile}
                
                JSONフォーマット:
                {{
                    "reason": "マッチング理由の説明",
                    "skills": ["スキル1", "スキル2", "スキル3"],
                    "score": 80  # 0-100のスコア
                }}
                """}
            ],
            temperature=0.7
        )
        
        import json
        result = json.loads(response.choices[0].message.content.strip())
        return result
        
    except Exception as e:
        app.logger.error(f"GPT API Error: {str(e)}")
        return {
            "reason": "プロフィール分析中にエラーが発生しました",
            "skills": [],
            "score": 0
        }


# ルート定義
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_student():
        records = LearningRecord.query.filter_by(student_id=current_user.id)\
            .order_by(LearningRecord.learning_date.desc()).limit(5).all()
        return render_template('student/dashboard.html', records=records)
    else:
        students = User.query.filter_by(role='student').all()
        return render_template('teacher/dashboard.html', students=students)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('ユーザー名またはパスワードが正しくありません', 'danger')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if not current_user.is_student():
        flash('学生以外はプロフィールを編集できません', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename, {'jpg', 'jpeg', 'png', 'gif'}):
                filename = secure_filename(file.filename)
                filepath = os.path.join('uploads/profiles', filename)
                full_path = os.path.join(app.static_folder, filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                file.save(full_path)
                
                if current_user.profile_photo:
                    old_path = os.path.join(app.static_folder, current_user.profile_photo)
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass
                
                current_user.profile_photo = filepath

        current_user.desired_job = request.form.get('desired_job')
        current_user.current_goal = request.form.get('current_goal')
        current_user.self_introduction = request.form.get('self_introduction')
        current_user.skills_and_interests = request.form.get('skills_and_interests')
        current_user.github_url = request.form.get('github_url')
        current_user.portfolio_url = request.form.get('portfolio_url')
        current_user.grade = request.form.get('grade')

        db.session.commit()
        flash('プロフィールが更新されました', 'success')
        return redirect(url_for('dashboard'))

    return render_template('student/edit_profile.html')

@app.route('/records')
@login_required
def view_records():
    query = LearningRecord.query

    category = request.args.get('category')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if current_user.is_student():
        query = query.filter_by(student_id=current_user.id)
    else:
        student_id = request.args.get('student_id')
        if student_id:
            query = query.filter_by(student_id=student_id)

    if category:
        query = query.filter_by(category=category)
    
    if date_from:
        try:
            date_from = datetime.strptime(f"{date_from}-01", '%Y-%m-%d').date()
            query = query.filter(LearningRecord.learning_date >= date_from)
        except ValueError:
            flash('開始日の形式が正しくありません', 'danger')

    if date_to:
        try:
            date_to = datetime.strptime(f"{date_to}-01", '%Y-%m-%d').date()
            query = query.filter(LearningRecord.learning_date <= date_to)
        except ValueError:
            flash('終了日の形式が正しくありません', 'danger')

    records = query.order_by(LearningRecord.learning_date.desc()).all()
    return render_template('shared/records.html', records=records)

@app.route('/record/new', methods=['GET', 'POST'])
@login_required
def new_record():
    if not current_user.is_student():
        flash('学生のみが記録を作成できます', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            if request.form['period_type'] == 'single':
                learning_date_str = request.form.get('learning_date')
                if not learning_date_str:
                    raise ValueError("日付が入力されていません")
                learning_date = datetime.strptime(f"{learning_date_str}-01", '%Y-%m-%d').date()
                end_date = None
            else:
                start_date_str = request.form.get('start_date')
                end_date_str = request.form.get('end_date')
                if not start_date_str or not end_date_str:
                    raise ValueError("開始日または終了日が入力されていません")
                learning_date = datetime.strptime(f"{start_date_str}-01", '%Y-%m-%d').date()
                end_date = datetime.strptime(f"{end_date_str}-01", '%Y-%m-%d').date()

            record = LearningRecord(
                student_id=current_user.id,
                title=request.form['title'],
                content=request.form['content'],
                category=request.form['category'],
                learning_date=learning_date,
                end_date=end_date,
                location=request.form['location'],
                achievement=request.form['achievement'],
                reflection=request.form['reflection'],
                skills=request.form['skills']
            )

            db.session.add(record)
            
            files = request.files.getlist('file')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    attachment = Attachment(filename=filename, file_path=file_path)
                    record.attachments.append(attachment)

            db.session.commit()
            flash('記録が作成されました', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('new_record'))

    return render_template('student/record_form.html')

@app.route('/record/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_record(id):
    record = LearningRecord.query.get_or_404(id)
    
    if current_user.is_student() and record.student_id != current_user.id:
        flash('自分の記録のみ編集できます', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            if current_user.is_student():
                record.title = request.form['title']
                record.content = request.form['content']
                record.category = request.form['category']
                record.location = request.form['location']
                record.achievement = request.form['achievement']
                record.reflection = request.form['reflection']
                record.skills = request.form['skills']

                if request.form['period_type'] == 'single':
                    learning_date_str = request.form.get('learning_date')
                    if not learning_date_str:
                        raise ValueError("日付が入力されていません")
                    record.learning_date = datetime.strptime(f"{learning_date_str}-01", '%Y-%m-%d').date()
                    record.end_date = None
                else:
                    start_date_str = request.form.get('start_date')
                    end_date_str = request.form.get('end_date')
                    if not start_date_str or not end_date_str:
                        raise ValueError("開始日または終了日が入力されていません")
                    record.learning_date = datetime.strptime(f"{start_date_str}-01", '%Y-%m-%d').date()
                    record.end_date = datetime.strptime(f"{end_date_str}-01", '%Y-%m-%d').date()

                files = request.files.getlist('file')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        attachment = Attachment(filename=filename, file_path=file_path)
                        record.attachments.append(attachment)
            else:
                record.feedback = request.form['feedback']
                record.feedback_teacher_id = current_user.id
                record.feedback_date = datetime.utcnow()

            db.session.commit()
            flash('記録が更新されました', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('edit_record', id=id))

    return render_template('student/record_form.html', record=record)

@app.route('/record/<int:id>/delete_attachment/<int:attachment_id>', methods=['POST'])
@login_required
def delete_attachment(id, attachment_id):
    record = LearningRecord.query.get_or_404(id)
    if current_user.is_student() and record.student_id != current_user.id:
        return jsonify({'success': False, 'message': '権限がありません'}), 403

    attachment = Attachment.query.get_or_404(attachment_id)
    if attachment.record_id != record.id:
        return jsonify({'success': False, 'message': '無効な要求です'}), 400

    try:
        os.remove(attachment.file_path)
    except OSError:
        pass

    db.session.delete(attachment)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/download/<int:attachment_id>')
@login_required
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    record = attachment.record

    if not current_user.is_teacher() and current_user.id != record.student_id:
        flash('このファイルにアクセスする権限がありません', 'danger')
        return redirect(url_for('dashboard'))

    return send_file(
        attachment.file_path,
        as_attachment=True,
        download_name=attachment.filename
    )

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 公開用ルート
@app.route('/students')
def public_student_list():
    students = User.query.filter_by(role='student').all()
    return render_template('student/public_student_list.html', students=students)

@app.route('/profile/<int:student_id>')
def public_student_profile(student_id):
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        abort(404)
    records = LearningRecord.query.filter_by(student_id=student.id)\
        .order_by(LearningRecord.learning_date.desc()).all()
    return render_template('student/public_profile.html', student=student, records=records)

@app.route('/record/<int:record_id>')
def public_record_detail(record_id):
    record = LearningRecord.query.get(record_id)
    if not record:
        abort(404)
    student = User.query.get(record.student_id)
    return render_template('student/public_record_detail.html', student=student, record=record)

# GPT検索API
@app.route('/api/student-search', methods=['POST'])
def search_students():
    """学生検索APIエンドポイント"""
    if not request.is_json:
        return jsonify({"error": "JSONリクエストが必要です"}), 400
        
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({"error": "検索クエリが必要です"}), 400

    try:
        # 学生データの取得と分析
        students = User.query.filter_by(role='student').all()
        matches = []

        for student in students:
            # プロフィール情報の整形
            profile = format_student_profile(student)
            
            # GPTによるマッチング分析
            match_result = analyze_student_match(query, profile)
            
            # スコアが50以上の学生のみを結果に含める
            if match_result["score"] >= 50:
                matches.append({
                    "id": student.id,
                    "full_name": student.full_name,
                    "department": student.department,
                    "profile_photo": url_for('static', filename=student.profile_photo) if student.profile_photo else None,
                    "match_reason": match_result["reason"],
                    "skills": match_result["skills"],
                    "score": match_result["score"]
                })

        # スコアの高い順にソート
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        # 上位5件のみを返す
        return jsonify({
            "recommendations": matches[:5]
        })

    except Exception as e:
        app.logger.error(f"Search Error: {str(e)}")
        return jsonify({
            "error": "検索処理中にエラーが発生しました"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)