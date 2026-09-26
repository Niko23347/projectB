import os

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from dotenv import load_dotenv
from supabase import create_client, Client
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ==================================================
# ENV
# ==================================================

load_dotenv()

DB_LINK = os.getenv("DB_LINK")
DB_KEY = os.getenv("DB_KEY")
FLASK_SECRET_KEY = "ttfu867"


if not DB_LINK:
    raise RuntimeError("DB_LINK не знайдено в .env")

if not DB_KEY:
    raise RuntimeError("DB_KEY не знайдено в .env")


# ==================================================
# SUPABASE
# ==================================================

supabase: Client = create_client(
    DB_LINK,
    DB_KEY
)


# ==================================================
# FLASK
# ==================================================

app = Flask(__name__)

app.secret_key = FLASK_SECRET_KEY


# ==================================================
# HOME / LOGIN
# ==================================================

@app.route("/")
def index():

    # Якщо користувач вже увійшов
    # відправляємо його на форум

    if "user_id" in session:
        return redirect(url_for("forum"))

    return render_template("index.html")


# ==================================================
# REGISTER
# ==================================================

@app.route("/register", methods=["POST"])
def register():

    name = request.form.get("name", "").strip()

    password = request.form.get("password", "")

    password_confirm = request.form.get(
        "password_confirm",
        ""
    )


    # Перевірка полів

    if not name or not password:

        return render_template(
            "index.html",
            error="Заповніть усі поля."
        )


    # Перевірка паролів

    if password != password_confirm:

        return render_template(
            "index.html",
            error="Паролі не співпадають."
        )


    # Мінімальна довжина

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
                error="Користувач з таким ім'ям вже існує."
            )


        # Хешуємо пароль

        password_hash = generate_password_hash(
            password
        )


        # Створюємо користувача

        result = (
            supabase
            .table("users")
            .insert({
                "name": name,
                "password": password_hash
            })
            .execute()
        )


        if not result.data:

            return render_template(
                "index.html",
                error="Не вдалося створити користувача."
            )


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


# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["POST"])
def login():

    name = request.form.get(
        "name",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )


    if not name or not password:

        return render_template(
            "index.html",
            error="Введіть ім'я та пароль."
        )


    try:

        # Знаходимо користувача

        result = (
            supabase
            .table("users")
            .select(
                "id, name, password"
            )
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


        # Зберігаємо користувача
        # у Flask session

        session["user_id"] = user["id"]

        session["user_name"] = user["name"]


        # Після login → форум

        return redirect(
            url_for("forum")
        )


    except Exception as e:

        print("LOGIN ERROR:", e)

        return render_template(
            "index.html",
            error="Помилка під час входу."
        )


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# ==================================================
# FORUM
# ==================================================

@app.route("/forum")
def forum():

    # Неавторизований користувач
    # не може зайти на форум

    if "user_id" not in session:

        return redirect(
            url_for("index")
        )


    try:

        # ==========================================
        # Отримуємо дискусії
        # ==========================================

        discussions_result = (
            supabase
            .table("forum")
            .select("*")
            .order(
                "discussion_id",
                desc=True
            )
            .execute()
        )

        discussions = discussions_result.data


        # ==========================================
        # Отримуємо користувачів
        # ==========================================

        users_result = (
            supabase
            .table("users")
            .select("id, name")
            .execute()
        )


        users = {
            user["id"]: user["name"]
            for user in users_result.data
        }


        # ==========================================
        # Додаємо ім'я автора
        # ==========================================

        for discussion in discussions:

            discussion["author_name"] = users.get(
                discussion["author_id"],
                "Unknown"
            )


        return render_template(
            "forum.html",
            discussions=discussions,
            user_name=session["user_name"]
        )


    except Exception as e:

        print("FORUM ERROR:", e)

        return "Помилка завантаження форуму", 500


# ==================================================
# CREATE DISCUSSION
# ==================================================

@app.route(
    "/create-discussion",
    methods=["POST"]
)
def create_discussion():

    # Перевірка авторизації

    if "user_id" not in session:

        return redirect(
            url_for("index")
        )


    questions = request.form.get(
        "questions",
        ""
    ).strip()


    description = request.form.get(
        "description",
        ""
    ).strip()


    if not questions:

        return redirect(
            url_for("forum")
        )


    try:

        # Створюємо питання

        supabase.table("forum").insert({

            "questions": questions,

            "description": description,

            # Автор береться з session
            # а не з HTML

            "author_id": session["user_id"]

        }).execute()


        return redirect(
            url_for("forum")
        )


    except Exception as e:

        print(
            "CREATE DISCUSSION ERROR:",
            e
        )

        return "Помилка створення питання", 500


# ==================================================
# SINGLE DISCUSSION
# ==================================================

@app.route(
    "/discussion/<int:discussion_id>"
)
def discussion(discussion_id):

    if "user_id" not in session:

        return redirect(
            url_for("index")
        )


    try:

        # ==========================================
        # Отримуємо питання
        # ==========================================

        discussion_result = (
            supabase
            .table("forum")
            .select("*")
            .eq(
                "discussion_id",
                discussion_id
            )
            .execute()
        )


        if not discussion_result.data:

            return "Питання не знайдено", 404


        discussion_data = (
            discussion_result.data[0]
        )


        # ==========================================
        # Автор питання
        # ==========================================

        author_result = (
            supabase
            .table("users")
            .select("name")
            .eq(
                "id",
                discussion_data["author_id"]
            )
            .execute()
        )


        if author_result.data:

            discussion_data["author_name"] = (
                author_result.data[0]["name"]
            )

        else:

            discussion_data["author_name"] = (
                "Unknown"
            )


        # ==========================================
        # Отримуємо відповіді
        # ==========================================

        answers_result = (
            supabase
            .table("questions")
            .select("*")
            .eq(
                "discussion_id",
                discussion_id
            )
            .order(
                "question_id"
            )
            .execute()
        )


        answers = answers_result.data


        # ==========================================
        # Отримуємо користувачів
        # ==========================================

        users_result = (
            supabase
            .table("users")
            .select("id, name")
            .execute()
        )


        users = {
            user["id"]: user["name"]
            for user in users_result.data
        }


        # ==========================================
        # Додаємо ім'я автора відповіді
        # ==========================================

        for answer in answers:

            answer["user_name"] = users.get(
                answer["user_id"],
                "Unknown"
            )


        return render_template(
            "discussion.html",

            discussion=discussion_data,

            answers=answers,

            user_name=session["user_name"]
        )


    except Exception as e:

        print(
            "DISCUSSION ERROR:",
            e
        )

        return "Помилка завантаження питання", 500


# ==================================================
# ADD ANSWER
# ==================================================

@app.route(
    "/discussion/<int:discussion_id>/answer",
    methods=["POST"]
)
def add_answer(discussion_id):

    if "user_id" not in session:

        return redirect(
            url_for("index")
        )


    answer = request.form.get(
        "answer",
        ""
    ).strip()


    if not answer:

        return redirect(
            url_for(
                "discussion",
                discussion_id=discussion_id
            )
        )


    try:

        # Перевіряємо, чи існує дискусія

        discussion_result = (
            supabase
            .table("forum")
            .select("discussion_id")
            .eq(
                "discussion_id",
                discussion_id
            )
            .execute()
        )


        if not discussion_result.data:

            return "Питання не знайдено", 404


        # ==========================================
        # Створюємо відповідь
        # ==========================================

        supabase.table("questions").insert({

            "answer": answer,

            # Поточний користувач

            "user_id": session["user_id"],

            # Поточна дискусія

            "discussion_id": discussion_id

        }).execute()


        return redirect(
            url_for(
                "discussion",
                discussion_id=discussion_id
            )
        )


    except Exception as e:

        print(
            "ANSWER ERROR:",
            e
        )

        return "Помилка створення відповіді", 500


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )