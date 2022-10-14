import time
import requests
import pytz
from datetime import datetime
from os import getenv
from babel.numbers import format_currency
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import RegisterForm, LoginForm, AddProductForm
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
from threading import Thread
from checker import run_checker

app = Flask(__name__)
app.config["SECRET_KEY"] = getenv("SECRET_KEY")
Bootstrap(app)

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DATABASE_URI")
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

IST = pytz.timezone("Asia/Kolkata")


class Member(UserMixin, db.Model):
    __tablename__ = "member"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    products = relationship("Product", backref="user")


class Product(db.Model):
    __tablename__ = "product"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("member.id"))
    product_name = Column(String, nullable=False)
    product_url = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    current_price = Column(String, nullable=False)
    user_price = Column(String, nullable=False)
    last_checked = Column(DateTime, nullable=False)


if app.before_first_request:
    db.create_all()


def int_price(data):
    temp_price = str(data)
    if "₹" in temp_price:
        temp_price = temp_price.replace("₹", "")
    if "," in temp_price:
        temp_price = temp_price.replace(",", "")
    try:
        return int(round(float(temp_price)))
    except ValueError:
        return None


def price(data):
    formatted_price = format_currency(data, "INR", locale="en_IN")[:-3]
    return formatted_price


def time_cal(checked_time):
    current_time = datetime.now(IST).replace(tzinfo=None)
    time_data = current_time - checked_time
    seconds = time_data.total_seconds()
    if seconds <= 60:
        return str(f"{int(seconds)} sec")
    elif seconds <= 3600:
        time = int(seconds / 60)
        return str(f"{time} min")
    elif seconds <= 86400:
        time = int(seconds / 3600)
        return str(f"{time} hr")
    else:
        time = int(seconds / 86400)
        if time == 1:
            return str(f"{time} day")
        return str(f"{time} days")


def valid_user(product_id):
    if current_user.id == Product.query.get(product_id).user_id:
        return True
    else:
        return False


@login_manager.user_loader
def load_user(user_id):
    return Member.query.filter_by(id=user_id).first()


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
        if Member.query.filter_by(email=email).first():
            flash("Email already exists, login")
            return redirect(url_for("login"))
        password = generate_password_hash(password=form.password.data, method="pbkdf2:sha256", salt_length=5)
        new_user = Member(
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
        user = Member.query.filter_by(email=email).first()
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
    cart = []
    if products:
        for each in products:
            product = {
                "id": each.id,
                "product_name": each.product_name,
                "product_url": each.product_url,
                "image_url": each.image_url,
                "current_price": each.current_price,
                "user_price": each.user_price,
                "last_checked": time_cal(each.last_checked),
            }
            cart.append(product)

    else:
        cart = 0
    return render_template("home.html", products=cart)


@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    form = AddProductForm()
    if form.validate_on_submit():
        url = form.product_url.data
        user_price = int_price(form.user_price.data)
        name = form.product_name.data.title()
        if "flipkart" not in url:
            flash("We support only flipkart links")
        elif int_price(user_price) is None:
            flash("Enter price without any symbols")
        else:
            response = requests.get(url, headers=header)
            web_data = response.text
            soup = BeautifulSoup(web_data, 'html.parser')
            image_url = soup.select_one(selector=".CXW8mj img").get("src")
            current_price = int_price(soup.select_one(selector="._25b18c ._30jeq3").get_text())
            current_time = datetime.now(IST).replace(tzinfo=None)
            if current_price <= user_price:
                data = {
                    "price": current_price,
                    "url": url
                }
                return render_template("result.html", result='available', product=data)
            else:
                new_product = Product(
                    product_name=name,
                    product_url=url,
                    image_url=image_url,
                    current_price=price(current_price),
                    user_price=price(user_price),
                    user_id=current_user.id,
                    last_checked=current_time
                )
                db.session.add(new_product)
                db.session.commit()
                return render_template("result.html", result='added')
    return render_template("add-product.html", form=form)


@app.route("/update/<int:product_id>", methods=["GET", "POST"], endpoint="update")
@login_required
def update(product_id):
    if valid_user(product_id):
        product = Product.query.get(product_id)
        form = AddProductForm(
            product_name=product.product_name,
            product_url=product.product_url,
            user_price=int_price(product.user_price)
        )

        if form.validate_on_submit():
            url = form.product_url.data
            user_price = int_price(form.user_price.data)
            name = form.product_name.data.title()
            if product.product_name == name and product.product_url == url and \
                    product.user_price == format_currency(user_price, "INR", locale="en_IN")[:-3]:
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
                current_price = int_price(soup.select_one(selector="._25b18c ._30jeq3").get_text())
                current_time = datetime.now(IST).replace(tzinfo=None)
                if current_price <= user_price:
                    product_details = {
                        "price": price(current_price),
                        "url": url,
                    }
                    db.session.delete(product)
                    db.session.commit()
                    return render_template("result.html", result="available", product=product_details)
                else:
                    product.product_name = name
                    product.product_url = url
                    product.image_url = image_url
                    product.user_price = price(user_price)
                    product.current_price = price(current_price)
                    product.last_checked = current_time
                    db.session.commit()
                    return render_template("result.html", result='updated')
        return render_template("update.html", form=form)
    else:
        return abort(403)


@app.route("/refresh/<int:product_id>", methods=["GET", "POST"])
@login_required
def refresh(product_id):
    product = Product.query.filter_by(id=product_id).first()
    product_url = product.product_url
    user_price = product.user_price
    response = requests.get(product_url, headers=header)
    web_data = response.text
    soup = BeautifulSoup(web_data)
    current_price = int_price(soup.select_one(selector="._25b18c ._30jeq3").get_text())
    current_time = datetime.now(IST).replace(tzinfo=None)
    if current_price <= int_price(user_price):
        product_details = {
            "price": price(current_price),
            "url": product_url,
        }
        db.session.delete(product)
        db.session.commit()
        return render_template("result.html", result="available", product=product_details)
    else:
        product.current_price = price(current_price)
        product.last_checked = current_time
        db.session.commit()
        return redirect(url_for('home'))


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


def ping():
    requests.get("https://flippi-git-nav.cloud.okteto.net/")
    print("Pinged")
    time.sleep(36000)


if __name__ == "__main__":
    t1 = Thread(target=run_checker)
    t1.start()
    t2 = Thread(target=ping)
    t2.start()
    app.run(host='0.0.0.0', port='5000')
