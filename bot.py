from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    CallbackContext, MessageHandler, Filters
)
import sqlite3
from datetime import datetime

TOKEN = "8775684678:AAEP4Eg8VDf4TFoyU5G89yxf_TadmLApEoc"
ADMIN_ID = 6669355865

CHANNEL_LINK = "https://t.me/mercx_official"
SUPPORT_LINK = "https://t.me/mercxsupport"

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    banned INTEGER DEFAULT 0,
    device TEXT,
    last_ip TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL,
    content TEXT,
    category_id INTEGER
);
""")
conn.commit()

# ================= HELPERS =================
def is_banned(uid):
    row = cursor.execute("SELECT banned FROM users WHERE user_id=?", (uid,)).fetchone()
    return row and row[0] == 1

def get_balance(uid):
    row = cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    return row[0] if row else 0

# ================= MENU =================
def menu(uid):
    kb = [
        [InlineKeyboardButton("🛒 Shop", callback_data="categories")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [
            InlineKeyboardButton("📢 Channel", url=CHANNEL_LINK),
            InlineKeyboardButton("💬 Support", url=SUPPORT_LINK)
        ]
    ]
    if uid == ADMIN_ID:
        kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

# ================= START =================
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id

    if is_banned(uid):
        update.message.reply_text("🚫 You are banned")
        return

    device = update.effective_user.username or "unknown"

    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id, device) VALUES(?,?)",
        (uid, device)
    )
    conn.commit()

    update.message.reply_text("💎 MERCX BOT", reply_markup=menu(uid))

# ================= CATEGORY =================
def add_category(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    name = " ".join(context.args)
    try:
        cursor.execute("INSERT INTO categories(name) VALUES(?)", (name,))
        conn.commit()
        update.message.reply_text("✅ Category added")
    except:
        update.message.reply_text("❌ Exists")

# ================= PRODUCTS =================
def add_product(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        name = context.args[0]
        price = float(context.args[1])
        cat = int(context.args[2])
        content = " ".join(context.args[3:])

        cursor.execute(
            "INSERT INTO products(name,price,content,category_id) VALUES(?,?,?,?)",
            (name, price, content, cat)
        )
        conn.commit()
        update.message.reply_text("✅ Product added")
    except:
        update.message.reply_text("Usage:\n/addproduct name price category_id content")

def del_product(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        pid = int(context.args[0])
        cursor.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
        update.message.reply_text("🗑 Deleted")
    except:
        update.message.reply_text("Usage: /delproduct id")

# ================= SHOP =================
def categories(q):
    cats = cursor.execute("SELECT * FROM categories").fetchall()

    if not cats:
        q.edit_message_text("❌ No categories")
        return

    text = "📂 Categories:\n\n"
    kb = []

    for c in cats:
        text += f"{c[0]} - {c[1]}\n"
        kb.append([InlineKeyboardButton(c[1], callback_data=f"cat_{c[0]}")])

    kb.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

def products(q, cid):
    items = cursor.execute("SELECT * FROM products WHERE category_id=?", (cid,)).fetchall()

    if not items:
        q.edit_message_text("❌ No products")
        return

    kb = [
        [InlineKeyboardButton(f"{i[1]} - ₦{i[2]}", callback_data=f"buy_{i[0]}")]
        for i in items
    ]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="categories")])

    q.edit_message_text("🛒 Select product", reply_markup=InlineKeyboardMarkup(kb))

# ================= BUY =================
def buy(q, context, pid):
    uid = q.from_user.id

    if is_banned(uid):
        q.answer("🚫 Banned", show_alert=True)
        return

    product = cursor.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()

    if not product:
        return

    bal = get_balance(uid)

    if bal < product[2]:
        q.answer("❌ Not enough balance", show_alert=True)
        return

    new_bal = bal - product[2]
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_bal, uid))
    conn.commit()

    q.edit_message_text(f"✅ Purchased\n\n{product[3]}\n\n💰 ₦{new_bal}")

# ================= BUTTON =================
def button(update: Update, context: CallbackContext):
    q = update.callback_query

    try:
        q.answer()
    except:
        pass

    d = q.data

    if d == "home":
        q.edit_message_text("💎 MERCX BOT", reply_markup=menu(q.from_user.id))

    elif d == "categories":
        categories(q)

    elif d.startswith("cat_"):
        products(q, int(d.split("_")[1]))

    elif d.startswith("buy_"):
        buy(q, context, int(d.split("_")[1]))

    elif d == "balance":
        q.edit_message_text(f"💰 ₦{get_balance(q.from_user.id)}")

# ================= AI =================
def ai(update: Update, context: CallbackContext):
    txt = update.message.text.lower()

    if "hi" in txt:
        r = "👋 Welcome!"
    elif "buy" in txt:
        r = "Use 🛒 Shop button"
    elif "balance" in txt:
        r = f"💰 ₦{get_balance(update.effective_user.id)}"
    else:
        r = "🤖 Use menu"

    update.message.reply_text(r)

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addcat", add_category))
    dp.add_handler(CommandHandler("addproduct", add_product))
    dp.add_handler(CommandHandler("delproduct", del_product))

    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, ai))

    print("✅ BOT RUNNING...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
