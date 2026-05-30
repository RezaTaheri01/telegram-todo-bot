import os
import django

from asgiref.sync import sync_to_async
from decouple import config

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from telegram.ext import (
    Application,
    MessageHandler,
    InlineQueryHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# -------------------------
# Django setup
# -------------------------

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from todos.models import Todo

# -------------------------
# Config
# -------------------------

TOKEN = config("TODO_BOT_TOKEN")
BOT_USERNAME = config("TODO_BOT_USERNAME", default="todo26bot")

# -------------------------
# HELP
# -------------------------

def help_text(bot_username: str):
    return (
        "🧠 Todo Bot\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "➕ Add todos (private chat only)\n"
        "Buy milk, Study, Work\n\n"
        "📌 View anywhere:\n"
        f"`@{bot_username}`\n\n"
        "🧩 Controls:\n"
        "✓ Toggle task\n"
        "🗑 Delete: /delete\n"
        "🗂 Close Tasks(Not done all)\n"
        "🔄 Refresh list\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ Tip: Separate multiple tasks with commas (,)"
    )

# -------------------------
# RENDER
# -------------------------

def render_todos(todos):
    active = [t for t in todos if not t.archived]

    lines = [
        "🧠 TASK BOARD",
        "────────────────────",
    ]

    if not active:
        lines.append("🎉 No active tasks")
        lines.append("────────────────────")
        return "\n".join(lines)

    pending = sum(1 for t in active if not t.completed)
    done = len(active) - pending

    lines.append(f"📊 Pending: {pending} | Done: {done}")
    lines.append("────────────────────")

    for i, todo in enumerate(active, 1):
        mark = "✓" if todo.completed else "•"
        text = todo.text.strip()

        if len(text) > 50:
            text = text[:47] + "..."

        lines.append(f"{mark} {text}\n")

    lines.append("────────────────────")

    return "\n".join(lines)

# -------------------------
# KEYBOARD
# -------------------------

def build_keyboard(todos, user_id):
    keyboard = []

    active = [t for t in todos if not t.archived]

    for todo in active:
        emoji = "↩️" if todo.completed else "✅"

        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {todo.text[:35]}",
                callback_data=f"toggle:{todo.id}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🔄 Refresh",
            callback_data=f"refresh:{user_id}",
        ),
        InlineKeyboardButton(
            "🗂 Close Todos",
            callback_data=f"archive:{user_id}",
        ),
    ])

    return InlineKeyboardMarkup(keyboard)

# -------------------------
# REFRESH UI
# -------------------------

async def refresh_ui(query, user_id):
    todos = await sync_to_async(list)(
        Todo.objects.filter(
            telegram_user_id=user_id,
            archived=False,
        ).order_by("id")
    )

    await query.edit_message_text(
        render_todos(todos),
        reply_markup=build_keyboard(todos, user_id),
    )

# -------------------------
# ADD TODOS
# -------------------------

async def save_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id

    tasks = [
        x.strip()
        for x in update.message.text.split(",")
        if x.strip()
    ]

    for task in tasks:
        await sync_to_async(Todo.objects.create)(
            telegram_user_id=user_id,
            text=task,
        )

    todos = await sync_to_async(list)(
        Todo.objects.filter(
            telegram_user_id=user_id,
            archived=False,
        ).order_by("id")
    )

    await update.message.reply_text(
        render_todos(todos),
        reply_markup=build_keyboard(todos, user_id),
    )

    await update.message.reply_text(
        f"✅ Added {len(tasks)} task(s)\nUse `@{BOT_USERNAME}`",
        parse_mode="Markdown",
    )

# -------------------------
# INLINE MODE
# -------------------------

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    user_id = query.from_user.id

    todos = await sync_to_async(list)(
        Todo.objects.filter(
            telegram_user_id=user_id,
            archived=False,
        ).order_by("id")
    )

    if not todos:
        result = InlineQueryResultArticle(
            id="start",
            title="Start bot first",
            description="No todos found",
            input_message_content=InputTextMessageContent(
                f"Start here: https://t.me/{BOT_USERNAME}"
            ),
        )

        await query.answer([result], cache_time=0)
        return

    result = InlineQueryResultArticle(
        id="todos",
        title="My Todo List",
        description=f"{len(todos)} tasks",
        input_message_content=InputTextMessageContent(
            render_todos(todos)
        ),
        reply_markup=build_keyboard(todos, user_id),
    )

    await query.answer([result], cache_time=0)

# -------------------------
# CALLBACKS
# -------------------------

async def todo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id


    try:
        # ---------------- DELETE ----------------
        if query.data == "cancel_delete":
            await query.answer("Cancelled")
            await query.edit_message_text("❌ Delete mode cancelled.")
            return
        
        if query.data.startswith("delete:"):
            _, todo_id = query.data.split(":")

            todo = await sync_to_async(Todo.objects.get)(id=int(todo_id))

            if todo.telegram_user_id != user_id:
                await query.answer("Not yours", show_alert=True)
                return

            await sync_to_async(todo.delete)()

            await query.answer("🗑 Deleted")

            return await delete_command(update, context)
        # ---------------- REFRESH ----------------
        if query.data.startswith("refresh"):
            owner = query.data.split(":")[1]
            await query.answer("Refreshing...")
            return await refresh_ui(query, owner)

        # ---------------- ARCHIVE ----------------
        if query.data.startswith("archive"):
            owner = query.data.split(":")[1]

            if owner != str(user_id):
                await query.answer("Not allowed", show_alert=True)
                return

            await sync_to_async(
                Todo.objects.filter(
                    telegram_user_id=user_id,
                    archived=False,
                ).update
            )(archived=True)
            
            await query.edit_message_reply_markup(None)

            return

        # ---------------- TOGGLE ----------------        
        _, todo_id = query.data.split(":")

        todo = await sync_to_async(Todo.objects.get)(
            id=int(todo_id)
        )

        if todo.telegram_user_id != user_id:
            await query.answer("Not yours", show_alert=True)
            return
        else:
            await query.answer()
            

        todo.completed = not todo.completed
        await sync_to_async(todo.save)()

        return await refresh_ui(query, user_id)

    except Exception as e:
        print("Callback error:", e)

# -------------------------
# DELETE COMMAND
# -------------------------

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id

    todos = await sync_to_async(list)(
        Todo.objects.filter(
            telegram_user_id=user_id,
            archived=False,
        ).order_by("id")
    )

    if not todos:
        if update.message:
            await update.message.reply_text("No todos to delete.")
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "No todos to delete.",
                reply_markup=None,
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"🗑 {todo.text[:40]}",
                callback_data=f"delete:{todo.id}",
            )
        ]
        for todo in todos
    ]

    keyboard.append([
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data="cancel_delete",
        )
    ])

    markup = InlineKeyboardMarkup(keyboard)

    # SAFE RESPONSE TARGET
    if update.message:
        await update.message.reply_text(
            "Select a todo to delete:",
            reply_markup=markup,
        )

    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Select a todo to delete:",
            reply_markup=markup,
        )
        
# -------------------------
# START / HELP
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        help_text(context.bot.username),
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        help_text(context.bot.username),
        parse_mode="Markdown",
    )

# -------------------------
# MAIN
# -------------------------

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            save_todos,
        )
    )

    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(CallbackQueryHandler(todo_callback))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("delete", delete_command))

    print("Todo bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
