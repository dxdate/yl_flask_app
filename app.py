import os
import shutil
from datetime import datetime

import flask_login
from flask import Flask, render_template, redirect, request, flash
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, PasswordField
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'best secret key'
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/static/images'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
storage = '/static/images'


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(20), nullable=False)
    update_author = db.Column(db.String(20), nullable=True)

    # def __repr__(self):
    #     return f'<Article {self.id}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=False)
    password_hash = db.Column(db.String(20), nullable=False)
    reg_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_date = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


class LoginForm(FlaskForm):
    username = StringField('Имя', validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField('Войти')


@app.route('/')
def index():
    return render_template("index.html", one_article=Article.query.order_by(Article.date.desc(
    )).first(), new_users=User.query.order_by(User.id.desc()).limit(5).all())



@app.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    message = ''
    if request.method == 'POST':
        f = request.files['file']
        if f.filename.split('.')[1] == 'jpg':
            filename = f'{flask_login.current_user.id}.{f.filename.split(".")[1]}'
            f.save(secure_filename(filename))
            if os.path.isfile(f'static/images/{filename}'):
                os.remove(f'static/images/{filename}')
                shutil.move(filename, 'static/images/')

        else:
            message = 'Загрузите картинку в формате JPG или PNG'
            return render_template('upload.html', message=message)
        return redirect('/about')
    return render_template('upload.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter(User.username == form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            if not os.path.isfile(f'/static/images/{flask_login.current_user.id}'):
                shutil.copy('static/images/default_img.jpg', f'static/images'
                                                             f'/{flask_login.current_user.id}.jpg')
            return redirect('/')
        flash("Invalid username/password", 'error')
        return redirect('/login')
    return render_template('login.html', form=form)


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
        article.update_author = flask_login.current_user.username
        try:
            db.session.commit()
            return redirect('/posts')
        except Exception:
            return 'Ошибка'
    else:
        return render_template("posts_update.html", article=article)


@app.route('/create-article', methods=['POST', 'GET'])
@login_required
def create_article():
    if request.method == 'POST':
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']
        article = Article(title=title, intro=intro, text=text, author=flask_login.current_user.username)
        try:
            db.session.add(article)
            db.session.commit()
            return redirect('/posts')
        except Exception as e:
            print(e)
    else:
        return render_template("create-article.html")


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')


@app.route('/register', methods=['POST', 'GET'])
def register():
    msg = 'Регистрация'
    if request.method == 'POST':
        try:
            user = User(username=request.form['login'],
                        password_hash=generate_password_hash(request.form['pass']))
            if User.query.filter_by(username=request.form['login']).first():
                return render_template('register.html', msg='Имя занято')
            db.session.add(user)
            db.session.commit()
            return redirect('/about')
        except Exception as e:
            print(e)
    else:
        return render_template('register.html', msg=msg)


@app.route('/about')
@login_required
def about():
    user_posts = Article.query.filter_by(author=flask_login.current_user.username).all()
    updated_posts = Article.query.filter_by(update_author=flask_login.current_user.username).all()
    return render_template('about.html', date=flask_login.current_user, posts=user_posts,
                           updated_posts=updated_posts)


@app.route('/profile/<username>')
@login_required
def profile(username):
    user_posts = Article.query.filter_by(author=username).all()
    date = User.query.filter_by(username=username).first()

    updated_posts = Article.query.filter_by(update_author=username).all()
    return render_template('profile.html', date=date, posts=user_posts, updated_posts=updated_posts)


@app.route('/all_profiles')
@login_required
def all_profiles():
    profiles = User.query.all()
    return render_template('all_profiles.html', profiles=profiles)


if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
