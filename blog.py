from flask import Flask, render_template,flash, request, redirect, url_for,session,logging
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
import psycopg2
from functools import wraps
from datetime import datetime

# Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görmek için lütfen giriş yapın...","danger")
            return redirect(url_for("login"))
    return decorated_function

# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min = 4,max = 25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min = 5,max = 35)])
    email = StringField("Email Adresi",validators=[validators.Email(message = "Lütfen Geçerli Bir Email Adresi Girin...")])
    password = PasswordField("Parola:",validators=[
        validators.DataRequired(message = "Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname = "confirm",message="Parolanız Uyuşmuyor...")
    ])
    confirm = PasswordField("Parola Doğrula")
    
# Giriş Yap Formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola") 


app = Flask(__name__)
app.secret_key= "ybblog"

# Veritabanı konfigürasyonu
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myuser:memo1234@localhost/ybblogdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Article('{self.title}', '{self.author}', '{self.created_at}')"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# Makale Sayfası
@app.route("/articles")
def articles():
    try:
        articles = Article.query.all()
        if articles:
            return render_template("articles.html", articles=articles)
        else:
            flash("Henüz makale eklenmemiş.", "warning")
            return render_template("articles.html")
    except Exception as e:
        flash(f"Veritabanı hatası: {str(e)}", "danger")
        return render_template("articles.html")

# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    try:
        articles = Article.query.filter_by(author=session["username"]).all()
        print(f"Fetched articles for {session['username']}: {articles}")  # Debugging: Print fetched articles
        return render_template("dashboard.html", articles=articles)
    except Exception as e:
        flash(f"Veritabanı hatası: {str(e)}", "danger")
        return render_template("dashboard.html")

# Makale Güncelleme
@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    article = Article.query.get(id)
    if article is None or article.author != session["username"]:
        flash("Böyle bir makale bulunmuyor veya güncelleme yetkiniz yok.", "danger")
        return redirect(url_for("login"))

    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        article.title = form.title.data
        article.content = form.content.data
        db.session.commit()
        flash("Makale Başarıyla Güncellendi...", "success")
        return redirect(url_for("dashboard"))

    form.title.data = article.title
    form.content.data = article.content
    return render_template("edit.html", form=form)

# Makale Silme
@app.route("/delete/<int:id>")
@login_required
def delete(id):
    article = Article.query.get(id)
    if article and article.author == session["username"]:
        db.session.delete(article)
        db.session.commit()
        flash("Makale başarıyla silindi.", "success")
    else:
        flash("Böyle bir makale bulunmuyor veya silme yetkiniz yok.", "danger")
        return redirect(url_for("index"))
    return redirect(url_for("dashboard"))
    
#Kayıt Olma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        new_user = User(name=name, username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Başarıyla Kayıt Oldunuz...", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

# Login İşlemi
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        username = form.username.data
        password_entered = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and sha256_crypt.verify(password_entered, user.password):
            flash("Başarıyla Giriş Yaptınız...", "success")
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("index"))
        else:
            flash("Kullanıcı adı veya parola yanlış...", "danger")
            return redirect(url_for("login"))
    return render_template('login.html', form=form)

# Detay Sayfası
@app.route("/article/<int:id>")
def article(id):
    article = Article.query.get(id)
    if article:
        return render_template("article.html", article=article)
    else:
        flash("Böyle bir makale bulunmuyor...", "warning")
        return render_template("article.html", article=None)

# Logout İşlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Makale Ekleme
@app.route("/addarticle",methods = ["GET","POST"])
@login_required
def addarticle():
    form=ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        new_article = Article(title=title, author=session["username"], content=content)
        db.session.add(new_article)
        db.session.commit()

        print(f"Article added: {title}, {content}")  # Debugging: Print added article

        flash("Makale Başarıyla Eklendi...", "success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form=form)

# Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min = 5,max = 100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min = 10)])

# Arama URL
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    keyword = request.form.get("keyword")
    articles = Article.query.filter(Article.title.contains(keyword)).all()
    if not articles:
        message = "Aranan kelimeye uygun makale bulunamadı..."
        return render_template("articles.html", articles=articles, message=message)
    return render_template("articles.html", articles=articles)


if __name__ == "__main__":
    db.create_all()  # Create all tables
    app.run(debug=True)
