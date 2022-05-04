import os
import pathlib
import shutil
import flask_login

from datetime import datetime
from flask import Flask, render_template, redirect, request, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired


app = Flask(__name__)

app.config['SECRET_KEY'] = 'best secret key'
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = '/static/images'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)
storage = '/static/images'


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(20), nullable=False)
    update_author = db.Column(db.String(20), nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=False)
    password_hash = db.Column(db.String(20), nullable=False)
    reg_date = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(10), default='user')

    def __repr__(self):
        return f'{self.username} - {self.id}'

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
@login_required
def index():
    return render_template("index.html",
                           one_post=Post.query.order_by
                           (Post.date.desc()).first(),
                           new_users=User.query.order_by(User.id.desc())
                           .limit(2).all(),
                           username=flask_login.current_user.username)


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


@app.route('/add_admin/<int:id>')
@login_required
def add_admin(id):
    user = User.query.filter_by(id=id).first()

    user.role = 'admin'
    db.session.commit()
    return redirect(f'/profile/{user.username}')


@app.route('/change_login/<int:id>', methods=["POST", "GET"])
@login_required
def change_login(id):
    msg = ''
    user = User.query.filter_by(id=id).first()
    if request.method == 'POST':
        new_login = request.form['login']
        password = request.form['pass']
        if user.check_password(password=password):
            user.username = new_login
            db.session.commit()
        else:
            msg = 'Введены неверные данные'
            return render_template('change_login.html', msg=msg)
        return redirect(f'/about')
    else:
        return render_template('change_login.html')


@app.route('/change_password/<int:id>', methods=["POST", "GET"])
@login_required
def change_password(id):
    msg = ''
    user = User.query.filter_by(id=id).first()
    if request.method == 'POST':
        new_password = request.form['new_pass']
        password = request.form['pass']
        if user.check_password(password=password):
            user.set_password(new_password)
            db.session.commit()
        else:
            msg = 'Введены неверные данные'
            return render_template('change_password.html', msg=msg)
        return redirect(f'/about')
    else:
        return render_template('change_password.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.query(User).filter(User.username == form.username.data).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            print(flask_login.current_user.id)

            if pathlib.Path(f'/static/images/{str(flask_login.current_user.id)}.jpg').exists():
                print('copy')
                shutil.copy('static/images/default_img.jpg', f'static/images'
                                                             f'/{flask_login.current_user.id}.jpg')
            return redirect('/')

        flash("Invalid username/password", 'error')
        return redirect('/login')

    return render_template('login.html', form=form)


@app.route('/posts')
def posts():
    posts = Post.query.order_by(Post.date.desc()).all()
    return render_template("posts.html", posts=posts, role=flask_login.current_user.role)


@app.route('/posts/<int:id>')
def posts_detail(id):
    post = Post.query.get(id)
    return render_template("posts_detail.html", post=post, role=flask_login.current_user.role)


@app.route('/posts/<int:id>/delete')
@login_required
def posts_delete(id):
    post = Post.query.get_or_404(id)
    try:

        db.session.delete(post)
        db.session.commit()

        return redirect('/posts')

    except Exception:
        return 'Ошибка'


@app.route('/posts/<int:id>/update', methods=['POST', 'GET'])
@login_required
def posts_update(id):
    post = Post.query.get(id)

    if request.method == 'POST':
        post.title = request.form['title']
        post.intro = request.form['intro']
        post.text = request.form['text']
        post.update_author = flask_login.current_user.username

        try:
            db.session.commit()
            return redirect('/posts')
        except Exception:
            return 'Ошибка'
    else:
        return render_template("posts_update.html", post=post)


@app.route('/create-post', methods=['POST', 'GET'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']
        author = flask_login.current_user.username
        post = Post(title=title,
                    intro=intro,
                    text=text,
                    author=author)
        try:
            db.session.add(post)
            db.session.commit()
            return redirect('/posts')
        except Exception as e:
            print(e)
    else:
        return render_template("create-post.html")


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@app.route('/register', methods=['POST', 'GET'])
def register():
    msg = 'Регистрация'

    if request.method == 'POST':
        try:
            username = request.form['login']
            password_hash = generate_password_hash(request.form['pass'])
            user = User(username=username,
                        password_hash=password_hash)

            if User.query.filter_by(username=request.form['login']).first():
                return render_template('register.html', msg='Имя занято')

            elif len(request.form['login']) > 11:
                return render_template('register.html', msg='Имя слишком длинное')

            db.session.add(user)
            db.session.commit()

            return redirect('/about')

        except Exception as e:
            return e

    else:
        return render_template('register.html', msg=msg)


@app.route('/about')
@login_required
def about():
    user_posts = Post.query.filter_by(author=flask_login.current_user.username).all()
    updated_posts = Post.query.filter_by(update_author=flask_login.current_user.username).all()

    return render_template('about.html',
                           date=flask_login.current_user,
                           posts=user_posts,
                           updated_posts=updated_posts)


@app.route('/profile/<username>')
@login_required
def profile(username):
    if username == flask_login.current_user.username:
        user_posts = Post.query.filter_by(author=flask_login.current_user.username).all()
        updated_posts = Post.query.filter_by(update_author=flask_login.current_user.username).all()

        return render_template('about.html',
                               date=flask_login.current_user,
                               posts=user_posts,
                               updated_posts=updated_posts)
    
    user_posts = Post.query.filter_by(author=username).all()
    date = User.query.filter_by(username=username).first()
    updated_posts = Post.query.filter_by(update_author=username).all()

    return render_template('profile.html', date=date,
                           posts=user_posts,
                           updated_posts=updated_posts,
                           role=flask_login.current_user.role)


@app.route('/profile/<id>/delete')
@login_required
def profile_delete(id):
    msg = "Все профили"
    user = User.query.filter_by(id=id).first()
    db.session.delete(user)
    db.session.commit()
    profiles = User.query.all()
    return render_template('all_profiles.html',
                           profiles=profiles,
                           msg=msg)


@app.route('/all_profiles', methods=['POST', 'GET'])
@login_required
def all_profiles():
    msg = "Все профили"
    flag_btn_back = False

    if request.method == 'POST':
        search = f"%{request.form['find_profile']}%"
        profiles = User.query.filter(User.username.like(search)).all()
        msg = f"По вашему запросу <{request.form['find_profile']}> найдено:"
        flag_btn_back = True
        return render_template('all_profiles.html',
                               profiles=profiles,
                               msg=msg,
                               flag_btn_back=flag_btn_back)

    else:
        profiles = User.query.all()
        return render_template('all_profiles.html',
                               profiles=profiles,
                               msg=msg)


if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
