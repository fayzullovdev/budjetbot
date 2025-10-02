import telebot
import sqlite3
from datetime import datetime
from telebot import types
import matplotlib.pyplot as plt

API_TOKEN = "8290278259:AAEQ26ACa5ZZ9my3AlLaUccf91L8QVKEdyw"  # o'z tokeningizni yozing
bot = telebot.TeleBot(API_TOKEN)

# === DATABASE ===
con = sqlite3.connect("budget.db", check_same_thread=False)
cur = con.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS transactions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    note TEXT,
    category TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
con.commit()

# === START ===
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Daromad qo‘shish", "➖ Xarajat qo‘shish")
    markup.row("📊 Hisobot", "📂 Kategoriyalar")
    markup.row("📈 Grafik")
    bot.send_message(message.chat.id,
        "👋 Salom! Men sizning *Budjet bot*ingizman.\n"
        "Pul tushumlarini va chiqimlarini yozib boring.\n\n"
        "Quyidagi menyudan tanlang 👇",
        parse_mode="Markdown",
        reply_markup=markup)

# === DAROMAD ===
@bot.message_handler(func=lambda m: m.text == "➕ Daromad qo‘shish")
def add_income(message):
    msg = bot.send_message(message.chat.id, "💰 Qancha daromad tushdi? (masalan: `200000 ish haqi`)")
    bot.register_next_step_handler(msg, save_income)

def save_income(message):
    try:
        amount = float(message.text.split()[0])
        note = " ".join(message.text.split()[1:])
        cur.execute("INSERT INTO transactions(user_id, amount, note, category) VALUES (?,?,?,?)",
                    (message.from_user.id, amount, note, "Daromad"))
        con.commit()
        bot.reply_to(message, f"✅ Daromad qo‘shildi: {amount} so‘m ({note})")
    except:
        bot.reply_to(message, "❗ Format xato. Masalan: `200000 ish haqi`")

# === XARAJAT ===
@bot.message_handler(func=lambda m: m.text == "➖ Xarajat qo‘shish")
def add_expense(message):
    markup = types.InlineKeyboardMarkup()
    categories = ["🍞 Oziq-ovqat", "🚌 Transport", "🏠 Uy", "🎉 O‘yin-kulgi", "❓ Boshqa"]
    for cat in categories:
        markup.add(types.InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
    bot.send_message(message.chat.id, "📝 Xarajat kategoriyasini tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def choose_category(call):
    category = call.data.replace("cat_", "")
    msg = bot.send_message(call.message.chat.id, f"💸 {category} xarajat summasini kiriting. (masalan: `15000 non`)")
    bot.register_next_step_handler(msg, lambda m: save_expense(m, category))

def save_expense(message, category):
    try:
        amount = -abs(float(message.text.split()[0]))  # xarajat - bo‘ladi
        note = " ".join(message.text.split()[1:])
        cur.execute("INSERT INTO transactions(user_id, amount, note, category) VALUES (?,?,?,?)",
                    (message.from_user.id, amount, note, category))
        con.commit()
        bot.reply_to(message, f"✅ Xarajat yozildi: {abs(amount)} so‘m ({note}) [{category}]")
    except:
        bot.reply_to(message, "❗ Format xato. Masalan: `15000 non`")

# === HISOBOT ===
@bot.message_handler(func=lambda m: m.text == "📊 Hisobot")
def report(message):
    user_id = message.from_user.id
    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=?", (user_id,))
    total = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND amount > 0", (user_id,))
    income = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND amount < 0", (user_id,))
    expense = cur.fetchone()[0] or 0

    msg = (f"📊 *Hisobot:*\n\n"
           f"💰 Daromad: {income} so‘m\n"
           f"💸 Xarajat: {abs(expense)} so‘m\n"
           f"📌 Balans: {total} so‘m")
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# === GRAFIK ===
@bot.message_handler(func=lambda m: m.text == "📈 Grafik")
def grafik(message):
    user_id = message.from_user.id
    cur.execute("SELECT category, SUM(amount) FROM transactions WHERE user_id=? GROUP BY category", (user_id,))
    data = cur.fetchall()

    if not data:
        bot.send_message(message.chat.id, "❗ Grafik uchun ma'lumot yo‘q")
        return

    categories = [cat for cat, _ in data if cat != "Daromad"]
    values = [abs(val) for cat, val in data if cat != "Daromad"]

    plt.figure(figsize=(6,6))
    plt.pie(values, labels=categories, autopct='%1.1f%%', startangle=90)
    plt.title("📊 Xarajatlar bo‘yicha grafik")

    filename = f"grafik_{user_id}.png"
    plt.savefig(filename)
    plt.close()

    with open(filename, "rb") as photo:
        bot.send_photo(message.chat.id, photo, caption="📈 Sizning xarajatlaringiz grafigi")

# === RUN ===
bot.polling(none_stop=True)
