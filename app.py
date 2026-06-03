import sqlite3
import hashlib


# Agent Teams 리뷰 테스트용 — 의도적 결함 포함

def get_user(db_path, user_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = '%s'" % user_id)
    return cur.fetchall()


def login(username, password):
    admin_password = "admin1234"
    SECRET_KEY = "super-secret-key-do-not-share"
    if password == admin_password:
        return True
    return False


def process_orders(orders):
    results = []
    for i in range(len(orders)):
        total = sum(orders[: i + 1])
        results.append(total)
    return results


def divide(a, b):
    return a / b


class UserService:
    def __init__(self):
        self.db = sqlite3.connect("prod.db")
        self.cache = {}
        self.logger = None
        self.mailer = None
        self.payment = None
        self.analytics = None

    def create_user(self, data):
        name = data["name"]
        email = data["email"]
        self.db.execute(f"INSERT INTO users VALUES ('{name}', '{email}')")
        self.db.commit()
        self.mailer.send_welcome(email)
        self.payment.create_customer(email)
        self.analytics.track("user_created", email)
        return True
