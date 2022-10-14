import time
import pytz
import psycopg2
import smtplib
import requests
import random
from datetime import datetime, timedelta
from os import getenv
from bs4 import BeautifulSoup

db = psycopg2.connect(getenv("DATABASE_URI"))
cursor = db.cursor()

header = {
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,ta;q=0.6,zh-CN;q=0.5,zh;q=0.4",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/95.0.4638.69 Safari/537.36",
}

IST = pytz.timezone("Asia/Kolkata")


def price_converter(data):
    price = str(data)
    if "₹" in price:
        price = price.replace("₹", "")
    if "," in price:
        price = price.replace(",", "")
    return round(float(price))


def send_email(data):
    print("Sending mail...")
    email = getenv("EMAIL")
    password = getenv("PASSWORD")
    with smtplib.SMTP("smtp.mail.yahoo.com") as connection:
        connection.starttls()
        connection.login(user=email, password=password)
        connection.sendmail(
            from_addr=email,
            to_addrs=data['email'],
            msg=f"SUBJECT:Low price alert for {data['product_name']}\n\nHi {data['name']}, {data['product_name']} is "
                f"now available for {data['product_price']}.\nBuy it here\n{data['product_link']}".encode("utf-8")
        )

    print("Mail Sent")


def update():
    cursor.execute("SELECT * FROM Product")
    products_data = cursor.fetchall()
    for product in products_data:
        cursor.execute(f"SELECT name,email FROM Member WHERE id={product[1]};")
        user_data = cursor.fetchall()
        print(f"User: {user_data[0][0].title()}({product[1]}), Name: {product[2]}, Status: Checking...")
        product_link = product[3]
        user_price = price_converter(product[6])
        db_current_price = price_converter(product[5])
        response = requests.get(product_link, headers=header)
        web_data = response.text
        soup = BeautifulSoup(web_data, "html.parser")
        current_price_str = soup.select_one(selector="._25b18c ._30jeq3").get_text()
        current_price = price_converter(current_price_str)
        current_time = datetime.now(IST).replace(tzinfo=None)
        if current_price <= user_price:
            mail_data = {
                "name": f"{user_data[0][0].title()}",
                "email": f"{user_data[0][1]}",
                "product_name": f"{product[2]}",
                "product_link": product_link,
                "product_price": current_price_str,
            }
            send_email(mail_data)
            cursor.execute(f"DELETE FROM Product WHERE id={product[0]}")
            db.commit()
            print("Product Deleted")

        elif db_current_price != current_price:
            cursor.execute(f"UPDATE Product SET current_price='{current_price_str}',"
                           f" last_checked='{current_time}' WHERE id={product[0]};")
            db.commit()
            print("Price Updated")

        else:
            cursor.execute(f"UPDATE Product SET last_checked='{current_time}' WHERE id={product[0]};")
            db.commit()
            print(f"User: {user_data[0][0].title()}({product[1]}), Name: {product[2]}, Status: Checked")

        time.sleep(random.randint(8, 16))


def admin_panel():
    cursor.execute("SELECT * FROM Member")
    users = cursor.fetchall()
    print("USER LIST")
    for user in users:
        print(user)
    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()
    print("PRODUCTS LIST")
    for product in products:
        print(product)
    user = int(input("Enter the user id to Delete: "))
    cursor.execute(f"DELETE FROM Product WHERE user_id={user}")
    cursor.execute(f"DELETE FROM Member WHERE id={user}")
    db.commit()


def del_all():
    cursor.execute("DELETE FROM Member")
    cursor.execute("DELETE FROM Product")
    db.commit()


def run_checker():
    while True:
        update()
        print(f"Check completed at {datetime.now(IST).replace(tzinfo=None)}")
        time.sleep(3600)
