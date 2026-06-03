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

from todos.models import Todo, TodoList

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
        "✓ Toggle todo\n"
        "🗑 Delete: /delete\n"
        "🗂 Close all todos\n"
        "🔄 Refresh list\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ Tip: Separate multiple todos with commas (,)"
    )

# -------------------------
# RENDER
# -------------------------

def render_todos(todos):
    active = [t for t in todos]

    lines = [
        "🧠 TODO BOARD",
        "────────────────────",
    ]

    if not active:
        lines.append("🎉 No active todos")
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

def build_keyboard(todos, user_id, todo_list_id):
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
            callback_data=f"refresh:{user_id}:{todo_list_id}",
        ),
        InlineKeyboardButton(
            "🗂 Close Todos",
            callback_data=f"archive:{user_id}:{todo_list_id}",
        ),
    ])

    return InlineKeyboardMarkup(keyboard)

# -------------------------
# Fetch Todos
# -------------------------

@sync_to_async
def get_create_todos(user_id):
    todo_list = (
        TodoList.objects
        .filter(
            telegram_user_id=user_id,
            archived=False,
        )
        .first()
    )

    if not todo_list:
        todo_list = TodoList.objects.create(
            telegram_user_id=user_id,
            name="My Tasks",
        )

    todos = list(
        Todo.objects.filter(
            todo_list=todo_list,
            archived=False,
        ).order_by("id")
    )

    return todos, todo_list.id


# sync_to_async with thread_sensitive=False (better performance for read-only operations)
@sync_to_async(thread_sensitive=False)
def get_todos(user_id):
    todo_list = (
        TodoList.objects
        .filter(
            telegram_user_id=user_id,
            archived=False,
        )
        .first()
    )

    if not todo_list:
        return [], None

    todos = list(
        Todo.objects.filter(
            todo_list=todo_list,
            archived=False,
        ).order_by("id")
    )

    return todos, todo_list.id


# sync_to_async with thread_sensitive=False (better performance for read-only operations)
@sync_to_async(thread_sensitive=False)
def get_archived_todos(todo_list_id):
    todo_list_exist = TodoList.objects.filter(
        id=todo_list_id,
        archived=True,
    ).exists()

    if not todo_list_exist:
        return []

    return list(Todo.objects.filter(
        todo_list=todo_list_id,
        archived=True,
        ).order_by("id"))

# -------------------------
# REFRESH UI
# -------------------------

async def refresh_ui(query, user_id):
    todos, todo_list_id = await get_create_todos(user_id)

    try:
        await query.edit_message_text(
            render_todos(todos),
            reply_markup=build_keyboard(todos, user_id, todo_list_id),
        )
    except Exception as e:
        pass

# -------------------------
# ADD TODOS
# -------------------------


async def save_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id

    todos = [
        x.strip()
        for x in update.message.text.split(",")
        if x.strip()
    ]
    
    if not todos:
        await update.message.reply_text(
            "Please enter at least one todo."
        )
        return
    
    todo_list = await sync_to_async(TodoList.objects.get_or_create)(
        telegram_user_id=user_id,
        archived=False,
    )

    for todo in todos:
        await sync_to_async(Todo.objects.create)(
            todo_list=todo_list[0],
            text=todo,
        )

    todos_all, todo_list_id = await get_create_todos(user_id)

    await update.message.reply_text(
        render_todos(todos_all),
        reply_markup=build_keyboard(todos_all, user_id, todo_list_id),
    )

    await update.message.reply_text(
        f"✅ Added {len(todos)} todo(s)\nUse `@{BOT_USERNAME}`",
        parse_mode="Markdown",
    )

# -------------------------
# INLINE MODE
# -------------------------

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    user_id = query.from_user.id
    
    todos, todo_list_id = await get_todos(user_id)

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
        description=f"{len(todos)} todos",
        input_message_content=InputTextMessageContent(
            render_todos(todos)
        ),
        reply_markup=build_keyboard(todos, user_id, todo_list_id),
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
            
            try:
                todo = await sync_to_async(Todo.objects.select_related("todo_list").get)(id=int(todo_id))
            except Todo.DoesNotExist:
                await query.answer("Todo not found", show_alert=True)
                await query.edit_message_reply_markup(reply_markup=None)
                return
            
            if todo.archived:
                await query.answer("Todo is not active to delete", show_alert=True)
                await query.edit_message_reply_markup(reply_markup=None)
                return
            
            if todo.todo_list.telegram_user_id != user_id:
                await query.answer("Not yours", show_alert=True)
                return

            await sync_to_async(todo.delete)()

            await query.answer("🗑 Deleted")

            return await delete_command(update, context)
        
        # ---------------- REFRESH ----------------
        if query.data.startswith("refresh"):
            owner = query.data.split(":")[1]
            todo_list_id = query.data.split(":")[2]
            
            try:
                todo_list = await sync_to_async(TodoList.objects.get)(id=int(todo_list_id))
            except TodoList.DoesNotExist:
                await query.answer("List not found", show_alert=True)
                return
            
            if todo_list.archived:
                todos = await get_archived_todos(todo_list_id)
                await query.answer("Already archived", show_alert=True)
                await query.edit_message_text(render_todos(todos),
                                              reply_markup=None)
                return
            
            await query.answer("Refreshing...")
            return await refresh_ui(query, owner)

        # ---------------- ARCHIVE ----------------
        if query.data.startswith("archive"):
            owner = query.data.split(":")[1]
            todo_list_id = query.data.split(":")[2]
            
            try:
                todo_list = await sync_to_async(TodoList.objects.get)(id=int(todo_list_id))
            except TodoList.DoesNotExist:
                await query.answer("List not found", show_alert=True)
                return

            if todo_list.telegram_user_id != user_id:
                await query.answer("Not yours", show_alert=True)
                return
            
            if todo_list.archived:
                todos = await get_archived_todos(todo_list_id)
                await query.answer("Already archived", show_alert=True)
                await query.edit_message_text(render_todos(todos),
                                              reply_markup=None)
                return

            # Archive on empty todo_list
            await sync_to_async(
                Todo.objects.filter(
                    todo_list=todo_list,
                    archived=False,
                ).update
            )(archived=True)
            
            todo_list.archived = True
            await sync_to_async(todo_list.save)()
            
            await query.edit_message_reply_markup(None)

            return

        # ---------------- TOGGLE ----------------        
        _, todo_id = query.data.split(":")

        try:
            todo = await sync_to_async(Todo.objects.select_related("todo_list").get)(id=int(todo_id))
        except Todo.DoesNotExist:
            await query.answer("Todo not found, Please refresh.")
            return
            # return await refresh_ui(query, user_id)
        
        if todo.archived:
            await query.answer("Todo list was archived, Close it!")
            return

        if todo.todo_list.telegram_user_id != user_id:
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
    
    todos, _ = await get_create_todos(user_id)

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
   
    
async def todo_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    todos, todo_list_id = await get_create_todos(user_id)

    await update.message.reply_text(
        render_todos(todos),
        reply_markup=build_keyboard(todos, user_id, todo_list_id),
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
    app.add_handler(CommandHandler("todos",  todo_list))
    app.add_handler(CommandHandler("delete", delete_command))

    print("Todo bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
