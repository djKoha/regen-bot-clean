# -*- coding: utf-8 -*-

import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)
from rapidfuzz import fuzz
from groq import Groq


# -----------------------------
# 1️⃣ ENV файлни юклаш
# -----------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

client = Groq(api_key=GROQ_API_KEY)


# -----------------------------
# 2️⃣ JSON базани ўқиш / сақлаш
# -----------------------------
def load_data():
    if not os.path.exists("data.json"):
        return {}

    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -----------------------------
# 3️⃣ Кирилл → Лотин
# -----------------------------
def translit_to_latin(text):
    mapping = {
        "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo",
        "ж":"j","з":"z","и":"i","й":"y","к":"k","л":"l","м":"m",
        "н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u",
        "ф":"f","х":"x","ц":"ts","ч":"ch","ш":"sh","щ":"sh",
        "ъ":"","ь":"","э":"e","ю":"yu","я":"ya",
        "қ":"q","ғ":"g","ҳ":"h","ў":"o"
    }

    result = ""
    for char in text.lower():
        result += mapping.get(char, char)

    return result


# -----------------------------
# 4️⃣ AI жавоб (Groq)
# -----------------------------
async def get_ai_response(text):

    clinic_info = """
    ReGen klinikasi Buxoro shahar Mustaqillik ko'chasi xxx uyda joylashgan.
    Orinter: Markaziy bank to'g'risi.
    Faqat klinika haqida javob ber.
    """

    if any("а" <= c.lower() <= "я" for c in text):
        instruction = "Жавобни фақат кирилл алифбосида бер."
    else:
        instruction = "Javobni faqat lotin alifbosida ber."

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": clinic_info},
            {"role": "system", "content": instruction},
            {"role": "user", "content": text}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content


# -----------------------------
# 5️⃣ Админ: /add
# -----------------------------
async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz.")
        return

    text = update.message.text.replace("/add", "").strip()

    if "|" not in text:
        await update.message.reply_text("Format: /add kalit1, kalit2 | javob")
        return

    parts = text.split("|")
    keywords_part = parts[0].strip()
    answer = parts[1].strip()

    keywords = [k.strip().lower() for k in keywords_part.split(",")]

    data = load_data()

    for key in keywords:
        data[key] = answer

    save_data(data)

    await update.message.reply_text("✅ Bir nechta kalit so'z qo'shildi.")


# -----------------------------
# 6️⃣ Админ: /delete
# -----------------------------
async def delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Format: /delete savol")
        return

    question = context.args[0].lower()
    data = load_data()

    if question in data:
        del data[question]
        save_data(data)
        await update.message.reply_text("❌ O'chirildi.")
    else:
        await update.message.reply_text("Topilmadi.")


# -----------------------------
# 7️⃣ Одатий хабарлар
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip().lower()
    data = load_data()

    latin_text = translit_to_latin(user_text)

    best_match = None
    highest_score = 0

    for question in data:
        score = fuzz.partial_ratio(latin_text, question.lower())
        if score > highest_score:
            highest_score = score
            best_match = question

    if highest_score >= 55:
        reply = data[best_match]
    else:
        reply = await get_ai_response(user_text)

    await update.message.reply_text(reply)


# -----------------------------
# 8️⃣ Ботни ишга тушириш
# -----------------------------
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("add", add_question))
app.add_handler(CommandHandler("delete", delete_question))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ Bot ishga tushdi...")
app.run_polling()