"""
Dejaf Tadlu — Telegram Ordering Bot
====================================
Lets customers browse the catalog, build a cart, and check out inside Telegram.
On checkout, a full order summary (items, quantities, subtotal, VAT, total,
customer name + address) is sent straight to the shop owner's Telegram chat.

Setup instructions are in README.md. Short version:
    1. pip install -r requirements.txt
    2. Copy .env.example to .env and fill in BOT_TOKEN (and later OWNER_CHAT_ID)
    3. python bot.py
"""

import os
import logging
from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from products import PRODUCTS, CATEGORIES

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")  # can be blank until you run /myid once
VAT_RATE = 0.15
SHOP_NAME = "Dejaf Tadlu (ደጃፍ - ታደሉ)"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}

# In-memory storage. Resets if the bot restarts.
# carts:    {chat_id: {product_id: qty}}
# checkout: {chat_id: {"stage": "name"|"address", "name": str}}
carts: dict[int, dict[int, int]] = {}
checkout_state: dict[int, dict] = {}


def fmt_etb(amount: float) -> str:
    return f"ETB {amount:,.2f}"


def unit_price(product: dict) -> int:
    return product["sale"] if product["sale"] is not None else product["price"]


def cart_lines(chat_id: int):
    cart = carts.get(chat_id, {})
    lines = []
    for pid, qty in cart.items():
        p = PRODUCTS_BY_ID.get(pid)
        if not p or qty <= 0:
            continue
        price = unit_price(p)
        lines.append({"product": p, "qty": qty, "unit": price, "line_total": price * qty})
    return lines


def cart_totals(chat_id: int):
    lines = cart_lines(chat_id)
    subtotal = sum(l["line_total"] for l in lines)
    vat = subtotal * VAT_RATE
    total = subtotal + vat
    return subtotal, vat, total


# ---------- Menus ----------

def main_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍 Browse Categories", callback_data="menu:categories")],
            [InlineKeyboardButton("🧺 View Cart", callback_data="menu:cart")],
        ]
    )


def categories_keyboard():
    buttons = []
    row = []
    for i, cat in enumerate(CATEGORIES, 1):
        row.append(InlineKeyboardButton(cat, callback_data=f"cat:{cat}"))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(cat: str):
    buttons = []
    for p in PRODUCTS:
        if p["cat"] != cat:
            continue
        price = unit_price(p)
        label = f"{p['name']} — {fmt_etb(price)}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"add:{p['id']}")])
    buttons.append([InlineKeyboardButton("⬅ Back to Categories", callback_data="menu:categories")])
    return InlineKeyboardMarkup(buttons)


def cart_keyboard(chat_id: int):
    buttons = []
    for line in cart_lines(chat_id):
        pid = line["product"]["id"]
        buttons.append(
            [
                InlineKeyboardButton(f"➖", callback_data=f"dec:{pid}"),
                InlineKeyboardButton(f"{line['product']['name']} x{line['qty']}", callback_data="noop"),
                InlineKeyboardButton(f"➕", callback_data=f"inc:{pid}"),
            ]
        )
    if cart_lines(chat_id):
        buttons.append([InlineKeyboardButton("✅ Checkout", callback_data="checkout:start")])
        buttons.append([InlineKeyboardButton("🗑 Clear Cart", callback_data="cart:clear")])
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)


def cart_text(chat_id: int) -> str:
    lines = cart_lines(chat_id)
    if not lines:
        return "Your cart is empty. Browse the catalog to add something!"
    parts = [f"🧺 *Your Cart*\n"]
    for l in lines:
        parts.append(f"{l['qty']} x {l['product']['name']} — {fmt_etb(l['line_total'])}")
    subtotal, vat, total = cart_totals(chat_id)
    parts.append("")
    parts.append(f"Subtotal: {fmt_etb(subtotal)}")
    parts.append(f"VAT (15%): {fmt_etb(vat)}")
    parts.append(f"*Total: {fmt_etb(total)}*")
    return "\n".join(parts)


# ---------- Command handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Selam! Welcome to *{SHOP_NAME}* 🛍\n\n"
        "Browse our catalog and order right here in Telegram.",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Utility command so the shop owner can find their own chat id."""
    await update.message.reply_text(
        f"Your chat ID is: `{update.effective_chat.id}`\n\n"
        "If you're the shop owner, put this in your .env file as OWNER_CHAT_ID "
        "and restart the bot.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    checkout_state.pop(chat_id, None)
    await update.message.reply_text("Checkout cancelled.", reply_markup=main_menu_keyboard())


# ---------- Button handler ----------

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data == "noop":
        return

    if data == "menu:main":
        await query.edit_message_text(
            f"*{SHOP_NAME}* 🛍\n\nWhat would you like to do?",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "menu:categories":
        await query.edit_message_text("Choose a department:", reply_markup=categories_keyboard())
        return

    if data.startswith("cat:"):
        cat = data.split(":", 1)[1]
        await query.edit_message_text(f"*{cat}*", reply_markup=products_keyboard(cat), parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("add:"):
        pid = int(data.split(":", 1)[1])
        carts.setdefault(chat_id, {})
        carts[chat_id][pid] = carts[chat_id].get(pid, 0) + 1
        await query.answer(text="Added to cart ✅", show_alert=False)
        return

    if data == "menu:cart":
        await query.edit_message_text(
            cart_text(chat_id), reply_markup=cart_keyboard(chat_id), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("inc:"):
        pid = int(data.split(":", 1)[1])
        carts.setdefault(chat_id, {})
        carts[chat_id][pid] = carts[chat_id].get(pid, 0) + 1
        await query.edit_message_text(
            cart_text(chat_id), reply_markup=cart_keyboard(chat_id), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("dec:"):
        pid = int(data.split(":", 1)[1])
        if chat_id in carts and pid in carts[chat_id]:
            carts[chat_id][pid] -= 1
            if carts[chat_id][pid] <= 0:
                del carts[chat_id][pid]
        await query.edit_message_text(
            cart_text(chat_id), reply_markup=cart_keyboard(chat_id), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "cart:clear":
        carts[chat_id] = {}
        await query.edit_message_text(
            cart_text(chat_id), reply_markup=cart_keyboard(chat_id), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "checkout:start":
        if not cart_lines(chat_id):
            await query.edit_message_text(
                "Your cart is empty.", reply_markup=cart_keyboard(chat_id)
            )
            return
        checkout_state[chat_id] = {"stage": "name"}
        await query.edit_message_text(
            "Let's get your order sent over.\n\nWhat's your *full name*?\n\n"
            "(Type /cancel anytime to stop)",
            parse_mode=ParseMode.MARKDOWN,
        )
        return


# ---------- Text handler (used only during checkout name/address steps) ----------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = checkout_state.get(chat_id)
    if not state:
        # Not in a checkout flow — just point them to the menu.
        await update.message.reply_text(
            "Use the menu below to browse or check your cart.",
            reply_markup=main_menu_keyboard(),
        )
        return

    text = update.message.text.strip()

    if state["stage"] == "name":
        if not text:
            await update.message.reply_text("Please type your full name.")
            return
        state["name"] = text
        state["stage"] = "address"
        await update.message.reply_text(
            "Thanks! And what's your *delivery address* (subcity / area / landmark)?",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if state["stage"] == "address":
        if not text:
            await update.message.reply_text("Please type your delivery address.")
            return
        state["address"] = text
        await finish_checkout(update, context, chat_id, state)
        checkout_state.pop(chat_id, None)
        return


async def finish_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, state: dict):
    lines = cart_lines(chat_id)
    subtotal, vat, total = cart_totals(chat_id)
    user = update.effective_user

    order_lines = [f"{l['qty']} x {l['product']['name']} — {fmt_etb(l['line_total'])}" for l in lines]
    contact_line = f"@{user.username}" if user.username else f"user ID {user.id}"
    summary = (
        f"🆕 *New order — {SHOP_NAME}*\n\n"
        + "\n".join(order_lines)
        + f"\n\nSubtotal: {fmt_etb(subtotal)}"
        + f"\nVAT (15%): {fmt_etb(vat)}"
        + f"\n*Total: {fmt_etb(total)}*"
        + f"\n\n👤 Name: {state['name']}"
        + f"\n📍 Address: {state['address']}"
        + f"\n💬 Telegram: {contact_line}"
    )

    # Notify the shop owner
    if OWNER_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(OWNER_CHAT_ID), text=summary, parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error("Failed to notify owner: %s", e)
    else:
        logger.warning("OWNER_CHAT_ID not set — order was not forwarded to the shop owner.")

    # Confirm to the customer
    await update.message.reply_text(
        "✅ Your order has been sent! We'll contact you shortly at the address you provided to "
        "confirm delivery and payment.\n\nThank you for shopping with us!",
        reply_markup=main_menu_keyboard(),
    )

    carts[chat_id] = {}


def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN is not set. Copy .env.example to .env and add your token from @BotFather."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
