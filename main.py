from os import getenv
import requests
from babel.numbers import format_currency
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import RegisterForm, LoginForm, AddProductForm
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config["SECRET_KEY"] = getenv("SECRET_KEY", "admin")
Bootstrap(app)

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DATABASE_URL", "sqlite:///dbase.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# LOGINMANAGER
login_manager = LoginManager()
login_manager.init_app(app)

header = {
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,ta;q=0.6,zh-CN;q=0.5,zh;q=0.4",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/95.0.4638.69 Safari/537.36",
}


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    products = relationship("Product", back_populates="user")


class Product(db.Model):
    __tablename__ = "product"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="products")
    product_name = Column(String, nullable=False)
    product_url = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    current_price = Column(String, nullable=False)
    user_price = Column(String, nullable=False)


if app.before_first_request:
    db.create_all()


def price_converter(data):
    price = str(data)
    if "₹" in price:
        price = price.replace("₹", "")
    if "," in price:
        price = price.replace(",", "")
    try:
        return int(round(float(price)))
    except ValueError:
        return None


def valid_user(product_id):
    if current_user.id == Product.query.get(product_id).user_id:
        return True
    else:
        return False


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        if User.query.filter_by(email=email).first():
            flash("Email already exists, login")
            return redirect(url_for("login"))
        password = generate_password_hash(password=form.password.data, method="pbkdf2:sha256", salt_length=5)
        new_user = User(
            name=form.name.data,
            email=email,
            password=password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash("Email doesn't exists")
        elif not check_password_hash(pwhash=user.password, password=form.password.data):
            flash("Incorrect Password")
        else:
            login_user(user)
            return redirect(url_for("home"))

    return render_template("login.html", form=form)


@app.route("/home")
def home():
    if not current_user.is_authenticated:
        return redirect(url_for("index"))
    products = current_user.products
    if len(products) == 0:
        products = 0
    return render_template("home.html", products=products)


@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    form = AddProductForm()
    if form.validate_on_submit():
        url = form.product_url.data
        user_price = price_converter(form.user_price.data)
        name = form.product_name.data.title()
        if "flipkart" not in url:
            flash("We support only flipkart links")
        elif price_converter(user_price) is None:
            flash("Enter price without any symbols")
        else:
            response = requests.get(url, headers=header)
            web_data = response.text
            soup = BeautifulSoup(web_data, 'html.parser')
            image_url = soup.select_one(selector=".CXW8mj img").get("src")
            current_price = price_converter(soup.select_one(selector="._25b18c ._30jeq3").get_text())
            if current_price <= user_price:
                data = {
                    "price": current_price,
                    "url": url
                }
                return render_template("result.html", added=False, product=data)
            else:
                new_product = Product(
                    product_name=name,
                    product_url=url,
                    image_url=image_url,
                    current_price=format_currency(current_price, "INR", locale="en_IN"),
                    user_price=format_currency(user_price, "INR", locale="en_IN"),
                    user=current_user
                )
                db.session.add(new_product)
                db.session.commit()
                return render_template("result.html", added=True)
    return render_template("add-product.html", form=form)


@app.route("/update/<int:product_id>", methods=["GET", "POST"], endpoint="update")
@login_required
def update(product_id):
    if valid_user(product_id):
        product = Product.query.get(product_id)
        form = AddProductForm(
            product_name=product.product_name,
            product_url=product.product_url,
            user_price=price_converter(product.user_price)
        )

        if form.validate_on_submit():
            url = form.product_url.data
            user_price = price_converter(form.user_price.data)
            name = form.product_name.data.title()
            if product.product_name == name and product.product_url == url and \
                    product.user_price == format_currency(user_price, "INR", locale="en_IN"):
                flash("Change anything to update")
            elif "flipkart" not in url:
                flash("We support only flipkart links")
            elif user_price is None:
                flash("Enter price without any symbols")
            else:
                response = requests.get(url, headers=header)
                web_data = response.text
                soup = BeautifulSoup(web_data, "html.parser")
                image_url = soup.select_one(selector=".CXW8mj img").get("src")
                current_price = price_converter(soup.select_one(selector="._25b18c ._30jeq3"))
                if current_price <= user_price:
                    product_details = {
                        "price": format_currency(current_price, "INR", locale="en_IN"),
                        "url": url,
                    }
                    db.session.delete(product)
                    db.session.commit()
                    return render_template("result.html", added=False, product=product_details)
                else:
                    product.product_name = name
                    product.product_url = url
                    product.image_url = image_url
                    product.user_price = format_currency(user_price, "INR", locale="en_IN")
                    product.current_price = format_currency(current_price, "INR", locale="en_IN")
                    db.session.commit()
                    return render_template("result.html", added=True, updated=True)
        return render_template("update.html", form=form)
    else:
        return abort(403)


@app.route("/delete/<int:product_id>", methods=["GET", "POST"], endpoint="delete")
@login_required
def delete(product_id):
    if valid_user(product_id):
        product = Product.query.filter_by(id=product_id).first()
        db.session.delete(product)
        db.session.commit()
        return redirect(url_for("home"))
    else:
        return abort(403)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run()
