# Todo Bot

A lightweight Telegram Todo bot built with Python, Django, and python-telegram-bot.

## Features

* ✅ Add multiple tasks at once
* ✅ Manage tasks from private chat
* ✅ Use inline mode in any chat
* ✅ Mark tasks as completed
* ✅ Reopen completed tasks
* ✅ Delete tasks
* ✅ Archive completed tasks
* ✅ Refresh task list
* ✅ Persistent storage with Django ORM

### Share Your Progress

Use inline mode to share your task board in any chat:

```text
@tododo26bot
```

Perfect for:

* 👨‍🏫 Sharing daily progress with a teacher or mentor
* 👥 Staying accountable with friends
* 📚 Tracking study goals in group chats
* 💼 Showing work progress to teammates

Only you can modify your tasks.

---

## Installation

### 1. Clone the repository

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it and install dependencies:

```bash
pip install -r req.txt
```

### 3. Configure environment variables

Create a `.env` file:

```env
BOT_TOKEN=your_bot_token
BOT_USERNAME=your_bot_username
```

Example:

```env
BOT_TOKEN=123456789:AA...
BOT_USERNAME=tododo26bot
```

### 4. Configure Django

Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Enable Inline Mode

Open Telegram and talk to @BotFather

```text
/setinline
```

Select your bot and enable inline mode.

### 6. Start the bot

```bash
python todo_bot.py
```

---

## Usage

### Add Tasks

Send a message to the bot in a private chat:

```text
Buy milk, Study, Do laundry
```

Each item separated by a comma becomes a new task.

### View Tasks Anywhere

Use inline mode in any chat:

```text
@tododo26bot
```

Select **My Todo List** to send your current task board.

### Delete Tasks

```text
/delete
```

Choose a task from the list to remove it.

---

## Commands

| Command   | Description          |
| --------- | -------------------- |
| `/start`  | Show welcome message |
| `/help`   | Show usage guide     |
| `/delete` | Delete a task        |

---

## Task Board

```text
🧠 TASK BOARD
────────────────────
📊 Pending: 2 | Done: 1
────────────────────
• Buy milk

✓ Study

• Do laundry

────────────────────
```

### Buttons

* ✅ Toggle task completion
* ↩️ Reopen completed task
* 🔄 Refresh task board
* 🗂 Close todo list

---

## Roadmap

* Multiple todo lists
* Focus timer
* Shared lists
* Assign tasks to others
* Productivity reports
* Completion statistics
* Accountability features

---

## Tech Stack

* Python
* Django ORM
* python-telegram-bot v20+
* SQLite

---

## License

MIT
