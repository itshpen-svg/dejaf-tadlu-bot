# Dejaf Tadlu — Telegram Ordering Bot

A Telegram bot that lets customers browse your catalog, build a cart, and check
out — with the full order (items, quantities, subtotal, VAT, total, customer
name and address) sent straight to your Telegram as a message.

Unlike a plain "message us on Telegram" link, this bot actually fills in the
order for the customer automatically, the same way the WhatsApp button on your
website does.

---

## 1. Create the bot on Telegram

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts (choose a name and a username ending
   in `bot`, e.g. `DejafTadluBot`).
3. BotFather will reply with a **token** that looks like
   `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`. Copy it.

## 2. Install and configure

Requires Python 3.10 or newer.

```bash
cd telegram-bot
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and paste your token:

```
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
OWNER_CHAT_ID=
```

Leave `OWNER_CHAT_ID` blank for now — you'll fill it in next.

## 3. Find your chat ID

1. Run the bot:
   ```bash
   python bot.py
   ```
2. Open Telegram, find your bot (search the username you gave it), and send
   `/myid`.
3. It will reply with your numeric chat ID. Copy it.
4. Stop the bot (Ctrl+C), paste that number into `.env` as `OWNER_CHAT_ID`,
   save, and run `python bot.py` again.

From now on, every completed order gets sent to that chat ID automatically.

## 4. Try it

In Telegram, send `/start` to your bot. You should see:

- **Browse Categories** — pick a department, then tap an item to add it
- **View Cart** — see what's in the cart, adjust quantities, or checkout
- **Checkout** — the bot asks for your name and delivery address, then sends
  the full order to you and confirms to the customer

## Keeping the bot online

Running `python bot.py` on your own computer only works while that computer
is on and connected. For a bot that's always reachable, deploy it somewhere
that runs 24/7. A few free or cheap options:

- **Railway.app** — connect your GitHub repo, add the same environment
  variables from `.env`, and it runs continuously on a free tier.
- **Render.com** — similar to Railway; deploy as a "Background Worker."
- **A small VPS** (e.g. a $5/month DigitalOcean droplet) — most control, but
  requires basic Linux server setup.

If you'd like, I can walk you through deploying to any of these once you're
ready.

## Keeping the catalog in sync with the website

`products.py` was generated from your website's product list at the time this
bot was built. If you add, remove, or reprice items on the website later,
either:

- Re-run `extract_products.py` against the latest `tadlu-store.html`
  (regenerates `products.py` automatically), or
- Edit `products.py` by hand — it's a plain Python list, safe to edit directly.

## Limitations to know about

- **Carts are stored in memory** — if the bot restarts, everyone's current
  cart is cleared. Fine for a small shop; ask me if you want this made
  persistent later (e.g. saved to a file or database).
- **No online payment** — same as the website right now, this bot collects
  orders but doesn't process payment. You confirm and arrange payment
  manually after receiving the order message.
- **Single admin** — orders go to one `OWNER_CHAT_ID`. If you want a second
  person to also receive orders (e.g. a staff member), ask and I can extend
  it to notify multiple chat IDs.
