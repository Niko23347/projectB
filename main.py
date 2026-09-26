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
FLASK_SECRET_KEY = "fk234jkd"


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
# HOME
# ==================================================

@app.route("/")
def index():

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

        password_hash = generate_password_hash(password)

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

        if not check_password_hash(
            user["password"],
            password
        ):

            return render_template(
                "index.html",
                error="Неправильне ім'я або пароль."
            )

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]

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

    if "user_id" not in session:
        return redirect(url_for("index"))

    try:

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

    if "user_id" not in session:
        return redirect(url_for("index"))

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

        supabase.table("forum").insert({

            "questions": questions,

            "description": description,

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
        return redirect(url_for("index"))

    try:

        # ------------------------------------------
        # DISCUSSION
        # ------------------------------------------

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

        # ------------------------------------------
        # DISCUSSION AUTHOR
        # ------------------------------------------

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

        # ------------------------------------------
        # ANSWERS
        # ------------------------------------------

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

        # ------------------------------------------
        # USERS
        # ------------------------------------------

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
        return redirect(url_for("index"))

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

        # Створюємо відповідь

        supabase.table("questions").insert({

            "answer": answer,

            "user_id": session["user_id"],

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
# DELETE DISCUSSION
# ==================================================

@app.route(
    "/delete-discussion/<int:discussion_id>",
    methods=["POST"]
)
def delete_discussion(discussion_id):

    if "user_id" not in session:
        return redirect(url_for("index"))

    try:

        # ------------------------------------------
        # Знаходимо дискусію
        # ------------------------------------------

        discussion_result = (
            supabase
            .table("forum")
            .select(
                "discussion_id, author_id"
            )
            .eq(
                "discussion_id",
                discussion_id
            )
            .execute()
        )

        if not discussion_result.data:

            return "Дискусію не знайдено", 404

        discussion_data = (
            discussion_result.data[0]
        )

        # ------------------------------------------
        # ПЕРЕВІРКА АВТОРА
        # ------------------------------------------

        if (
            discussion_data["author_id"]
            != session["user_id"]
        ):

            return (
                "Ви можете видаляти тільки "
                "свої дискусії",
                403
            )

        # ------------------------------------------
        # ВИДАЛЯЄМО ВІДПОВІДІ
        # ------------------------------------------

        supabase \
            .table("questions") \
            .delete() \
            .eq(
                "discussion_id",
                discussion_id
            ) \
            .execute()

        # ------------------------------------------
        # ВИДАЛЯЄМО ДИСКУСІЮ
        # ------------------------------------------

        supabase \
            .table("forum") \
            .delete() \
            .eq(
                "discussion_id",
                discussion_id
            ) \
            .execute()

        return redirect(
            url_for("forum")
        )

    except Exception as e:

        print(
            "DELETE DISCUSSION ERROR:",
            e
        )

        return (
            "Помилка видалення дискусії",
            500
        )


# ==================================================
# DELETE ANSWER
# ==================================================

@app.route(
    "/delete-answer/<int:question_id>",
    methods=["POST"]
)
def delete_answer(question_id):

    if "user_id" not in session:
        return redirect(url_for("index"))

    try:

        # ------------------------------------------
        # ЗНАХОДИМО ВІДПОВІДЬ
        # ------------------------------------------

        answer_result = (
            supabase
            .table("questions")
            .select(
                "question_id, user_id, discussion_id"
            )
            .eq(
                "question_id",
                question_id
            )
            .execute()
        )

        if not answer_result.data:

            return "Відповідь не знайдено", 404

        answer_data = answer_result.data[0]

        # ------------------------------------------
        # ПЕРЕВІРКА АВТОРА
        # ------------------------------------------

        if (
            answer_data["user_id"]
            != session["user_id"]
        ):

            return (
                "Ви можете видаляти тільки "
                "свої відповіді",
                403
            )

        discussion_id = (
            answer_data["discussion_id"]
        )

        # ------------------------------------------
        # ВИДАЛЯЄМО ВІДПОВІДЬ
        # ------------------------------------------

        supabase \
            .table("questions") \
            .delete() \
            .eq(
                "question_id",
                question_id
            ) \
            .execute()

        return redirect(
            url_for(
                "discussion",
                discussion_id=discussion_id
            )
        )

    except Exception as e:

        print(
            "DELETE ANSWER ERROR:",
            e
        )

        return (
            "Помилка видалення відповіді",
            500
        )


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )