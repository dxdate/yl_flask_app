from datetime import datetime
from flask import Flask, render_template, redirect, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required

app = Flask(__name__)
app.config['SECRET_KEY'] = 'best key'
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # def __repr__(self):
    #     return f'<Article {self.id}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    reg_date = db.Column(db.DateTime, default=datetime.utcnow)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/posts')
def posts():
    articles = Article.query.order_by(Article.date.desc()).all()
    return render_template("posts.html", articles=articles)


@app.route('/posts/<int:id>')
def posts_detail(id):
    article = Article.query.get(id)
    return render_template("posts_detail.html", article=article)


@app.route('/posts/<int:id>/delete')
@login_required
def posts_delete(id):
    article = Article.query.get_or_404(id)
    try:
        db.session.delete(article)
        db.session.commit()
        return redirect('/posts')
    except Exception:
        return 'Ошибка'


@app.route('/posts/<int:id>/update', methods=['POST', 'GET'])
@login_required
def posts_update(id):
    article = Article.query.get(id)
    if request.method == 'POST':
        article.title = request.form['title']
        article.intro = request.form['intro']
        article.text = request.form['text']
        try:
            db.session.commit()
            return redirect('/posts')
        except Exception:
            return 'Ошибка'
    else:

        return render_template("posts_update.html", article=article)


@app.route('/create-article', methods=['POST', 'GET'])
def create_article():
    if request.method == 'POST':
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']

        article = Article(title=title, intro=intro, text=text)

        try:
            db.session.add(article)
            db.session.commit()
            return redirect('/posts')
        except Exception:
            return 'Ошибка'
    else:
        return render_template("create-article.html")


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        try:
            user = User(name=request.form['login'],
                        password=generate_password_hash(request.form['pass']))
            db.session.add(user)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            print(e)
    else:
        return render_template('login.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        try:
            user = User(name=request.form['login'],
                        password=generate_password_hash(request.form['pass']))
            db.session.add(user)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            print(e)
    else:
        return render_template('register.html')


if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
