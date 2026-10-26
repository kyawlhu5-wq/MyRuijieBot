import hashlib
import hmac
import json
import os
import threading
from flask import Flask, jsonify
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- CONFIGURATION (အသင့်ထည့်သွင်းပြီးပါပြီ) ---
TOKEN = "8903822712:AAEv_ck_vazHjzQLmk_NF4vkTmo9AgfCqic"
LICENSE_FILE = "licenses.json"
ADMIN_USER_ID = 8775300748  # သင့်ရဲ့ Admin ID
SHARED_SECRET = "MY_ULTIMATE_SECRET_KEY_2026"  # Replit ဘက်က bot.py ထဲတွင်လည်း ဤ Key အတိုင်း တူရပါမည်

app = Flask(__name__)


def load_licenses():
  if not os.path.exists(LICENSE_FILE):
    return {}
  try:
    with open(LICENSE_FILE, "r") as f:
      return json.load(f)
  except:
    return {}


def save_licenses(data):
  with open(LICENSE_FILE, "w") as f:
    json.dump(data, f, indent=4)


def generate_secure_token(user_id):
  """User ID တစ်ခုချင်းစီအတွက် လုံခြုံသော Token တည်ဆောက်ခြင်း"""
  return hmac.new(
      SHARED_SECRET.encode(), str(user_id).encode(), hashlib.sha256
  ).hexdigest()


# --- Flask API Endpoint (Replit ဘက်က လှမ်းတောင်းမည့် API) ---
@app.route("/check_license/<user_id>", methods=["GET"])
def api_check_license(user_id):
  licenses = load_licenses()
  user_data = licenses.get(str(user_id))

  if not user_data or not user_data.get("active"):
    return jsonify({"status": "expired"}), 403

  # မှန်ကန်ပါက status အပြင် secure token ပါ တစ်ခါတည်း ပေးလိုက်မည်
  secure_token = generate_secure_token(user_id)
  return (
      jsonify(
          {
              "status": "active",
              "expiry": user_data["expiry"],
              "token": secure_token,
          }
      ),
      200,
  )


# --- Telegram Admin Panel Commands & Buttons ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_USER_ID:
    return
  keyboard = [
      [InlineKeyboardButton("👥 လိုင်စင်စာရင်းကြည့်ရန်", callback_data="list_users")],
      [InlineKeyboardButton("➕ လိုင်စင်ထည့်ရန်", callback_data="add_prompt")],
      [InlineKeyboardButton("❌ လိုင်စင်ပိတ်ရန်", callback_data="revoke_prompt")],
  ]
  await update.message.reply_text(
      "👑 **Ultimate License Control Panel**",
      reply_markup=InlineKeyboardMarkup(keyboard),
      parse_mode="Markdown",
  )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  if query.data == "list_users":
    licenses = load_licenses()
    if not licenses:
      await query.edit_message_text("📁 လိုင်စင်စာရင်း မရှိသေးပါ။")
      return
    text = "📋 **Active Licenses:**\n\n"
    for uid, info in licenses.items():
      status = "🟢 Active" if info.get("active") else "🔴 Expired"
      text += f"🆔 `{uid}`\n📅 Exp: {info['expiry']} | {status}\n-------------------\n"
    await query.edit_message_text(text, parse_mode="Markdown")

  elif query.data == "add_prompt":
    context.user_data["state"] = "WAITING_ADD"
    await query.edit_message_text(
        "✍️ ပုံစံအတိုင်း ပို့ပါ:\n`UserID YYYY-MM-DD`\n(ဥပမာ: `8775300748"
        " 2026-12-31`)",
        parse_mode="Markdown",
    )

  elif query.data == "revoke_prompt":
    context.user_data["state"] = "WAITING_REVOKE"
    await query.edit_message_text(
        "✍️ ပိတ်လိုသည့် **Telegram User ID** ကို ရိုက်ပို့ပါ။", parse_mode="Markdown"
    )


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_USER_ID:
    return
  state = context.user_data.get("state")
  text = update.message.text.strip()
  licenses = load_licenses()

  if state == "WAITING_ADD":
    try:
      parts = text.split()
      user_id, expiry = parts[0], parts[1]
      licenses[user_id] = {"expiry": expiry, "active": True}
      save_licenses(licenses)
      context.user_data["state"] = None
      await update.message.reply_text(f"✅ Added: `{user_id}` till `{expiry}`", parse_mode="Markdown")
    except:
      await update.message.reply_text("❌ ပုံစံမမှန်ပါ။ ပြန်ကြိုးစားပါ။")

  elif state == "WAITING_REVOKE":
    user_id = text
    if user_id in licenses:
      licenses[user_id]["active"] = False
      save_licenses(licenses)
      context.user_data["state"] = None
      await update.message.reply_text(f"🚫 Revoked: `{user_id}`", parse_mode="Markdown")
    else:
      await update.message.reply_text("❌ User ID မတွေ့ပါ။")


def run_flask():
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


def main():
  threading.Thread(target=run_flask, daemon=True).start()
  app_bot = Application.builder().token(TOKEN).build()
  app_bot.add_handler(CommandHandler("start", start))
  app_bot.add_handler(CallbackQueryHandler(button_handler))
  app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
  app_bot.run_polling()


if __name__ == "__main__":
  main()
