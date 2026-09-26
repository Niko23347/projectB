import os

from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash


# =========================
# ENV
# =========================

load_dotenv()

DB_LINK = os.getenv("DB_LINK")
DB_KEY = os.getenv("DB_KEY")
FLASK_SECRET_KEY = "hbyuft56"

if not DB_LINK or not DB_KEY:
    raise RuntimeError("DB_LINK або DB_KEY не знайдено в .env")



# =========================
# SUPABASE
# =========================

supabase: Client = create_client(
    DB_LINK,
    DB_KEY
)


# =========================
# FLASK
# =========================

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY


# =========================
# LOGIN PAGE
# =========================

@app.route("/")
def index():

    # Якщо вже залогінений —
    # одразу на форум
    if "user_id" in session:
        return redirect(url_for("forum"))

    return render_template("index.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["POST"])
def register():

    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    if not name or not password:
        return render_template(
            "index.html",
            error="Заповніть усі поля."
        )

    if password != password_confirm:
        return render_template(
            "index.html",
            error="Паролі не співпадають."
        )

    if len(password) < 6:
        return render_template(
            "index.html",
            error="Пароль повинен містити мінімум 6 символів."
        )

    try:

        # Перевіряємо, чи існує користувач
        existing_user = (
            supabase
            .table("users")
            .select("id")
            .eq("name", name)
            .execute()
        )

        if existing_user.data:
            return render_template(
                "index.html",
                error="Користувач з таким ім'ям уже існує."
            )

        # Хешуємо пароль
        password_hash = generate_password_hash(password)

        # Створюємо користувача
        supabase.table("users").insert({
            "name": name,
            "password": password_hash
        }).execute()

        return render_template(
            "index.html",
            success="Реєстрація успішна! Тепер увійдіть."
        )

    except Exception as e:

        print("REGISTER ERROR:", e)

        return render_template(
            "index.html",
            error="Помилка під час реєстрації."
        )


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["POST"])
def login():

    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")

    if not name or not password:
        return render_template(
            "index.html",
            error="Введіть ім'я та пароль."
        )

    try:

        result = (
            supabase
            .table("users")
            .select("id, name, password")
            .eq("name", name)
            .limit(1)
            .execute()
        )

        if not result.data:
            return render_template(
                "index.html",
                error="Неправильне ім'я або пароль."
            )

        user = result.data[0]

        # Перевіряємо пароль
        if not check_password_hash(
            user["password"],
            password
        ):
            return render_template(
                "index.html",
                error="Неправильне ім'я або пароль."
            )

        # Зберігаємо дані користувача
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]

        # ПЕРЕХОДИМО НА ФОРУМ
        return redirect(url_for("forum"))

    except Exception as e:

        print("LOGIN ERROR:", e)

        return render_template(
            "index.html",
            error="Помилка під час входу."
        )


# =========================
# FORUM
# =========================

@app.route("/forum")
def forum():

    # Якщо не залогінений —
    # повертаємо на login
    if "user_id" not in session:
        return redirect(url_for("index"))

    try:

        # Отримуємо всі дискусії
        result = (
            supabase
            .table("forum")
            .select("*")
            .order("discussion_id", desc=True)
            .execute()
        )

        discussions = result.data

        return render_template(
            "forum.html",
            discussions=discussions,
            user_name=session["user_name"]
        )

    except Exception as e:

        print("FORUM ERROR:", e)

        return "Помилка завантаження форуму", 500


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True)