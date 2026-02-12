# modules/state.py
import asyncio

# Словари для динамических состояний
setup_messages = {}
channel_locks = {}
room_modes = {}
last_rename_times = {}
created_channels = {}
channel_bases = {}

# Очередь для статистики или других задач
stat_queue = asyncio.Queue()

# Пользователи и недели
users = {}
weeks = []

