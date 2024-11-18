from app import db, User

# 新しい学生ユーザーを作成
new_student = User(
    username="student3",            # ユーザー名
    full_name="D",          # 氏名
    student_id="s2322002",            # 学籍番号
    department="データサイエンス学部", # 学科
    role="student"                    # ロール
)
new_student.set_password("password")  # パスワード設定
db.session.add(new_student)
db.session.commit()                   # データベースに保存

print("新しい学生が追加されました")
