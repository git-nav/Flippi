from flask_wtf import FlaskForm
from wtforms.fields.html5 import EmailField
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Email, URL, DataRequired, Length


class RegisterForm(FlaskForm):
    name = StringField(label="Name", validators=[DataRequired()])
    email = EmailField(label="Email", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password", validators=[DataRequired(), Length(min=5)])
    submit = SubmitField(label="Submit")


class LoginForm(FlaskForm):
    email = EmailField(label="Email", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password", validators=[DataRequired(), Length(min=5)])
    submit = SubmitField(label="Submit")


class AddProductForm(FlaskForm):
    product_name = StringField(label="Product Name", validators=[DataRequired()])
    product_url = StringField(label="Product Url", validators=[DataRequired(), URL()])
    user_price = StringField(label="Your Price", validators=[DataRequired()])
    submit = SubmitField(label="Submit")
