import random
import threading
from getpass import getpass

from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)


class Game:
    """Создает игру морской бой для двух игроков.

    Атрибуты:
        player1 (int): telegram ID первого игрока.
        player2 (int): telegram ID второго игрока.
        board1 (list[list[int]]): Поле 10x10 первого игрока.
        board2 (list[list[int]]): Поле 10x10 второго игрока.
        timeout_timer (threading.Timer): Таймер бездействия.
        current_turn (int): ID игрока, чей сейчас ход.
    """
    def __init__(self, player1, player2):
        """Создание новой партии между двумя игроками и генерация игровых полей.

        Аргументы:
            player1 (int): Telegram ID первого игрока.
            player2 (int): Telegram ID второго игрока.
        """
        self.player1 = player1
        self.player2 = player2
        self.board1 = self.generate_board()
        self.board2 = self.generate_board()
        self.current_turn = random.choice([player1, player2])
        self.timeout_timer = None
        self.reset_timeout_timer()
    
    def reset_timeout_timer(self):
        """Сбрасывает и запускает новый таймер бездействия (3 минуты).
        Если игрок не сделает ход за это время — он проигрывает.
        """
        if self.timeout_timer:
            self.timeout_timer.cancel()
        self.timeout_timer = threading.Timer(180, self.timeout_loss)
        self.timeout_timer.start()

    def timeout_loss(self):
        """Обрабатывает автопоражение текущего игрока из-за бездействия.
        Уведомляет обоих игроков и завершает игру.
        """
        loser = self.current_turn
        winner = self.player1 if loser == self.player2 else self.player2
        context = self.context  # Сохраняем контекст в момент старта игры

        context.bot.send_message(loser, "Вы не сделали ход в течение 3 минут. Вы проиграли, чем вы там заняты?!")
        context.bot.send_message(winner, "🎉 Ваш соперник не сделал ход вовремя. Вы победили!")

        games.pop(frozenset({self.player1, self.player2}), None)

    def generate_board(self):
        """Рандомно генерирует игровое поле 10x10 с размещёнными кораблями по правилам игры.

        Возвращает:
            list[list[int]]: поле с расставленными кораблями.
        """
        board = [[0 for _ in range(10)] for _ in range(10)]
        ship_sizes = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]

        for size in ship_sizes:
            placed = False
            attempts = 0
            while not placed and attempts < 1000:
                attempts += 1
                x = random.randint(0, 9)
                y = random.randint(0, 9)
                orientation = random.choice(['horizontal', 'vertical'])
                if self.can_place_ship(board, x, y, size, orientation):
                    self.place_ship(board, x, y, size, orientation)
                    placed = True
            if not placed:
                return self.generate_board()
        return board

    def can_place_ship(self, board, x, y, size, orientation):
        """Проверяет, можно ли разместить корабль заданного размера на позиции по правилам игры.

        Аргументы:
            board (list[list[int]]): Игровое поле.
            x (int): стартовая координата по оси X.
            y (int): стартовая координата по оси Y.
            size (int): размер корабля.
            orientation (str): ориентация корабля: 'horizontal' или 'vertical'.

        Возвращает:
            bool: True, если размещение возможно по правилам, иначе False.
        """
        if orientation == 'horizontal':
            if x + size > 10:
                return False
            for i in range(x, x + size):
                if board[y][i] != 0:
                    return False
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        ny = y + dy
                        nx = i + dx
                        if 0 <= ny < 10 and 0 <= nx < 10 and board[ny][nx] != 0:
                            return False
        else:
            if y + size > 10:
                return False
            for j in range(y, y + size):
                if board[j][x] != 0:
                    return False
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx = x + dx
                        ny = j + dy
                        if 0 <= nx < 10 and 0 <= ny < 10 and board[ny][nx] != 0:
                            return False
        return True

    def place_ship(self, board, x, y, size, orientation):
        """Размещает корабль на игровом поле.

        Аргументы:
            board (list[list[int]]): Игровое поле.
            x (int): стартовая координата по оси X.
            y (int): стартовая координата по оси Y.
            size (int): размер корабля.
            orientation (str): ориентация корабля: 'horizontal' или 'vertical'
        """
        if orientation == 'horizontal':
            for i in range(x, x + size):
                board[y][i] = 1
        else:
            for j in range(y, y + size):
                board[j][x] = 1

    def shot(self, shooter, coord):
        """Обрабатывает выстрел игрока и обновляет состояние игрового поля.

        Аргументы:
            shooter (int): ID игрока, который совершил выстрел.
            coord (tuple[int, int]): Координаты (x, y) выстрела.

        Возвращает:
            str: Результат выстрела — 'hit', 'miss', 'win', 'already', 'invalid'.
        """
        x, y = coord
        target_board = self.board2 if shooter == self.player1 else self.board1

        if not (0 <= x < 10 and 0 <= y < 10):
            return 'invalid'

        if target_board[y][x] in (2, -1, 3):
            return 'already'

        if target_board[y][x] == 1:
            target_board[y][x] = 2
            if self.check_ship_dead(target_board, x, y):
                self.mark_dead_ship(target_board, x, y)
            if self.check_win(shooter):
                return 'win'
            return 'hit'
        else:
            target_board[y][x] = -1
            self.current_turn = (
                self.player2 if shooter == self.player1 else self.player1
            )
            return 'miss'

    def check_ship_dead(self, board, x, y):
        """Проверка на то, потоплен ли корабль после удачного выстрела.

        Аргументы:
            board (list[list[int]]): Игровое поле.
            x (int): Координата X выстрела.
            y (int): Координата Y выстрела.

        Возвращает:
            bool: True, если корабль потоплен, в противном случае False.
        """
        ship_cells = self.find_ship_cells(board, x, y)
        return all(board[cy][cx] != 1 for cx, cy in ship_cells)

    def find_ship_cells(self, board, start_x, start_y):
        """Поиск клеток корабля, в зависимости от его стартовых коордиант.

        Аргументы:
            board (list[list[int]]): Игровое поле.
            start_x (int): стартовая координата X.
            start_y (int): стартовая координата Y.

        Возвращает:
            list[tuple[int, int]]: список координат клеток, где находится корабль
        """
        visited = set()
        queue = [(start_x, start_y)]
        ship_cells = []

        while queue:
            x, y = queue.pop(0)
            if (x, y) in visited:
                continue
            visited.add((x, y))
            if 0 <= x < 10 and 0 <= y < 10 and board[y][x] in (1, 2):
                ship_cells.append((x, y))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    queue.append((x + dx, y + dy))
        return ship_cells

    def mark_dead_ship(self, board, x, y):
        """Отмечает клетки корабля как уничтоженные после его потопления.

        Аргументы:
            board (list[list[int]]): Игровое поле.
            x (int): стартовая X попадания.
            y (int): стартовая Y попадания.
        """
        ship_cells = self.find_ship_cells(board, x, y)
        for cx, cy in ship_cells:
            board[cy][cx] = 3

    def check_win(self, shooter):
        """Проверка того, победил ли игрок после его хода.

        Аргументы:
            shooter (int): ID игрока, сделавшего ход.

        Возвращает:
            bool: True, если у противника не осталось кораблей, в противном False.
        """
        target_board = self.board2 if shooter == self.player1 else self.board1
        return all(1 not in row for row in target_board)


waiting = []
games = {}


def start(update: Update, context: CallbackContext):
    """Обрабатывает введение игроком команды /start.

    Отправляет пользователю приветственное сообщение с информацией.
    """
    update.message.reply_text("Привет! Это Морской бой. Используй /play чтобы начать игру.")


def play(update: Update, context: CallbackContext):
    """Обрабатывает ввеленую команду /play.

    Добавляет пользователя в очередь и запускает игру, если есть второй игрок уже в очереди ожидания.
    """
    if len(games) == 0:
        user_id = update.message.from_user.id

        if user_id in waiting:
            update.message.reply_text("Вы уже в очереди. Ожидаем второго игрока.")
            return

        waiting.append(user_id)
        if len(waiting) >= 2:
            player1 = waiting.pop(0)
            player2 = waiting.pop(0)
            game = Game(player1, player2)
            game.context = context
            games[frozenset({player1, player2})] = game
            context.bot.send_message(
                player1,
                f"Игра началась! Используйте команду /stop, чтобы досрочно завершить игру. Первый ход за {'вами' if game.current_turn == player1 else 'соперником'}.",
            )
            context.bot.send_message(
                player2,
                f"Игра началась! Используйте команду /stop, чтобы досрочно завершить игру. Первый ход за {'вами' if game.current_turn == player2 else 'соперником'}.",
            )
            send_boards(context, game)
        else:
            update.message.reply_text("Ожидаем второго игрока...")
    else:
        update.message.reply_text('Сейчас идёт другая игра.')


def stop(update: Update, context: CallbackContext):
    """Обрабатывает введенную команду /stop.

    Заканчивает текущую партию и очищает все активные сессии.
    """
    user_id = update.message.from_user.id

    for key in list(games.keys()):
        if user_id in key:
            game = games.pop(key)
            if game.timeout_timer:
                game.timeout_timer.cancel()
            opponent_id = game.player1 if user_id == game.player2 else game.player2

            update.message.reply_text("Вы остановили игру.")
            context.bot.send_message(opponent_id, "Противник завершил игру досрочно командой /stop.")
            return

    update.message.reply_text("Вы не участвуете в текущей игре.")


def send_boards(context, game):
    """Отправка игрокам игровых полей.

    Аргументы:
        context (CallbackContext): Контекст Telegram-бота — чат с игроком.
        game (Game): Текущая игровая партия.
    """
    for player in [game.player1, game.player2]:
        is_own = (player == game.player1)
        own_board = game.board1 if is_own else game.board2
        protivnik_board = game.board2 if is_own else game.board1

        own_display = draw_board(own_board, is_own=True)
        protivnik_display = draw_board(protivnik_board, is_own=False)
        context.bot.send_message(
            player,
            f"Ваше поле:\n{own_display}\n\nПоле соперника:\n{protivnik_display}"
        )


def draw_board(board, is_own=True):
    """Преобразует игровое поле в текстовый вид с эмодзи.

    Аргументы:
        board (list[list[int]]): Игровое поле 10x10.
        is_own (bool): True, если поле своё (корабли видны), False — поле противника.

    Возвращает:
        str: Представление поля в виде строк с эмодзи.
    """
    symbols = {
        0: '🟦',
        1: '🚢' if is_own else '🟦',
        -1: '⚪️',
        2: '💥',
        3: '💀',
    }
    rows = ['']
    nums = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    for y in range(10):
        row = [symbols.get(board[y][x], '🟦') for x in range(10)]
        rows.append(nums[y] + ''.join(row))
    return '\n'.join(rows)


def preobr_coord(coord_str):
    """Преобразует строку с координатой в числовой формат (x, y).

    Аргументы:
        coord_str (str): Строка вида "A1", "J10" и т.п.

    Возвращает:
        tuple[int, int] | None: Кортеж координат или None, если строка некорректна.
    """
    try:
        coord_str = coord_str.strip().upper()
        letter = coord_str[0]
        number = int(coord_str[1:])
        x = ord(letter) - ord('A')
        y = number - 1
        if 0 <= x < 10 and 0 <= y < 10:
            return x, y
        return None
    except (IndexError, ValueError):
        return None


def handle_message(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения игроков.

   Проверяет ход, обрабатывает координаты и обновляет состояние игры.

   Аргументы:
       update (Update): Объект(сообщение) обновления Telegram-бота.
       context (CallbackContext): контекст Telegram-бота с игроком.
   """
    user_id = update.message.from_user.id
    text = update.message.text

    game = None
    for key in list(games.keys()):
        if user_id in key:
            game = games[key]
            break

    if not game:
        update.message.reply_text("Сначала начните игру с помощью /play")
        return

    if game.current_turn != user_id:
        update.message.reply_text("Сейчас не ваш ход!")
        return

    coord = preobr_coord(text)
    if not coord:
        update.message.reply_text("Некорректные координаты. Пример: A1, J10")
        return

    result = game.shot(user_id, coord)
    game.reset_timeout_timer()
    protivnik = game.player1 if user_id == game.player2 else game.player2

    if result == 'hit':
        update.message.reply_text("✅ ТУУУУУДААААА! Вы продолжайте стрелять.")
        context.bot.send_message(protivnik, "😢 По вам попали")
        send_boards(context, game)
        if game.check_win(user_id):
            context.bot.send_message(user_id, "🎉 Вы победили!")
            context.bot.send_message(protivnik, "😢 Вы проиграли...")
            del games[frozenset((game.player1, game.player2))]
    elif result == 'miss':
        update.message.reply_text("❌ Промах! Ход переходит сопернику.")
        context.bot.send_message(protivnik, "😏 Фух, пронесло")
        send_boards(context, game)
    elif result == 'win':
        context.bot.send_message(user_id, "🎉 Вы победили!")
        context.bot.send_message(protivnik, "😢 Вы проиграли...")
        if game.timeout_timer:
                    game.timeout_timer.cancel()
        del games[frozenset((game.player1, game.player2))]
    elif result == 'already':
        update.message.reply_text("Вы уже стреляли сюда!")
    else:
        update.message.reply_text("Ошибка!")


def run_bot():
    """Запускает бота с использованием введеного токена.

    Регистрирует обработчики возможных команд и сообщений.
    """
    token = getpass("Введите токен вашего бота: ")
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("play", play))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()


bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

print("Бот запущен! Для остановки нажмите Ctrl+C или перезапустите сессию Colab")
