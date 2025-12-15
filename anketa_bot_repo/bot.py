import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import aiosqlite
import gspread
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials


# -----------------------------
# Конфиг
# -----------------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "").strip()
CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH", "").strip()
ADMIN_IDS = set(
    int(x.strip())
    for x in (os.getenv("ADMIN_IDS", "") or "").split(",")
    if x.strip().isdigit()
)

DB_PATH = "bot.db"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# -----------------------------
# Вопросы анкет
# -----------------------------
PARENT_FULL_QUESTIONS: List[str] = [
    "Укажите ваш юзернейм",
    "Фамилия, имя и отчество ребёнка.",
    "Возраст ребенка.",
    "Дата рождения. (дд.мм.гггг)",
    "В какой школе учится Ваш ребенок?",
    "Рост ребенка (примерно).",
    "Вес ребенка (примерно).",
    "Бывал ли ребенок в нашем лагере ранее? (Да/Нет)",
    "Как вы о нас узнали?",
    "Хочет ли ваш ребёнок поехать в лагерь?",
    "Бывал ли ребенок в лагере ранее?",
    "Если да, то что ему понравилось в лагере?",
    "Что не понравилось?",
    "Ребёнок самостоятельно принял решение ехать в лагере в этом году или вы этому способствовали?",
    "Какие увлечения у вашего ребёнка? (кружки, секции, хобби)",
    "Есть ли у него противопоказания к занятиям спортом?",
    "Есть ли у ребёнка индивидуальная непереносимость продуктов питания, лекарств, аллергии?",
    "Часто ли ребёнок болеет, если да, то чем?",
    "Есть ли хронические заболевания, если да то какие?",
    "Были ли травмы (переломы, ушибы, сотрясения)?",
    "Назовите 5 прилагательных, которыми можно описать Вашего ребенка.",
    "Есть ли проблемы во взаимоотношениях со сверстниками или взрослыми?",
    "Чем ваш ребенок больше всего любит заниматься в свободное время?",
    "Умеет ли плавать?",
    "Какие предпочитает игры?",
    "Какие фильмы смотрит с большим удовольствием?",
    "Где и как ваш ребенок обычно проводит каникулы?",
    "Какой из видов отдыха ему нравится больше всего?",
    "Легко ли идет на контакт?",
    "Как адаптируется в новых условиях?",
    "Как реагирует на критику?",
    "Если плачет, что Вы обычно делаете?",
    "Как вы охарактеризуете своего ребёнка в плане самостоятельности и самообслуживания?",
    "Были случаи когда ваш ребёнок дрался с другими ребятами?",
    "Как ваш ребёнок взаимодействует со своими одноклассниками?",
    "Ваш ребёнок более общительный или робкий?",
    "Какой основной круг общения вашего ребёнка? С кем он больше всего проводит времени?",
    "Как в вашему ребёнку относятся его одноклассники?",
    "Сообщили ли вы ребенку, что в лагере запрещены телефоны и различные гаджеты у детей? (Да/Нет)",
    "Говорили ли вы ребенку, что запрещена привезенная с собой еда? (Да/Нет)",
    "Планируете ли вы заказать фотосессию со смены? (Да/Нет)",
    "Дополнительные сведения о ребенке, на что следует обратить внимание вожатым при общении с ним (что Вы хотите сообщить нам о ребенке и его особенностях)",
    "Какие Ваши ожидания от смены? Что мы должны постараться сделать?",
    "По возможности добавьте ссылку на фотографию Вашего ребенка, которая наиболее точно его характеризует (необязательный вопрос)",
    "По желанию добавьте ссылку на социальную сеть Вашего ребенка (необязательный вопрос)",
    "ФИО мамы",
    "Телефон мобильный, рабочий, домашний (мама)",
    "ФИО папы",
    "Телефон мобильный, рабочий, домашний (папа)",
    "Адрес и место нахождения родителей на время лагеря",
    "ФИО, телефон третьих лиц, имеющих право забирать ребенка (если есть)",
]

PARENT_SHORT_QUESTIONS: List[str] = [
    "Укажите ваш юзернейм",
    "Фамилия, имя и отчество ребёнка.",
    "Возраст ребенка.",
    "Дата рождения.",
    "В какой школе учится Ваш ребенок?",
    "Рост ребенка (примерно).",
    "Вес ребенка (примерно).",
    "Есть ли у него противопоказания к занятиям спортом?",
    "Есть ли у ребёнка индивидуальная непереносимость продуктов питания, лекарств, аллергии?",
    "Есть ли хронические заболевания, если да, то какие?",
    "Сообщили ли вы ребенку, что в лагере запрещены телефоны и различные гаджеты у детей? (Да/Нет)",
    "Говорили ли вы ребенку, что запрещена привезенная с собой еда? (Да/Нет)",
    "Планируете ли вы заказать фотосессию со смены? (Да/Нет)",
    "Дополнительные сведения о ребенке, на что следует обратить внимание вожатым при общении с ним (что Вы хотите сообщить нам о ребенке и его особенностях).",
    "Какие Ваши ожидания от смены? Что мы должны постараться сделать?",
    "ФИО мамы.",
    "Телефон мобильный, рабочий, домашний (мама).",
    "ФИО папы.",
    "Телефон мобильный, рабочий, домашний (папа).",
    "Адрес и место нахождения родителей на время лагеря.",
    "ФИО, телефон третьих лиц, имеющих право забирать ребенка (если есть).",
]

CHILD_FULL_QUESTIONS: List[str] = [
    "Как тебя зовут (Имя)?",
    "Твоя фамилия?",
    "Сколько тебе лет?",
    "Выбери несколько качеств вожатого, которые ты считаешь самыми важными (не более 5). Напиши через запятую.\n"
    "Варианты: Должен заменять в лагере родителей; Должен быть тебе другом; Должен быть красивым; Справедливым; "
    "Отзывчивым; Строгим; Общительным; Творческим; Должен много знать; Должен помогать; Уметь петь и танцевать; "
    "Быть бодрым и весёлым; Знать много интересных игр; Постоянно находиться рядом; Быть спортивным; "
    "Знать много смешных историй; Быть душой компании; Вести здоровый образ жизни; Понимать, когда нужна поддержка; "
    "Уметь сплотить ребят из отряда.",
    "Ты едешь в лагерь впервые или ты уже до этого был в лагерях, если да, то сколько раз?",
    "Хочешь ли ты поехать в лагерь? (Да/Нет)",
    "Чего больше всего ты ждешь от лагеря? И чего бы тебе хотелось попробовать больше всего? (выбери не менее 2-х) Напиши через запятую.\n"
    "Варианты: Найти новых друзей; Стать одной командой с ребятами; Приобрести новые знания, умения; "
    "Укрепить свое здоровье; Улучшить физическую подготовку; Выступить на сцене; Просто отдохнуть; "
    "Весело провести время; Побыть без родителей; Показать себя и свои умения.",
    "А ты занимаешься какими-то видами спорта? Давно? Есть ли у тебя награды, достижения? А какими хочешь заниматься?",
    "Если не секрет, ты едешь один(одна), или с тобой едет кто-то из друзей?",
    "С кем ты хочешь поселиться в одной комнате?",
    "Ты хочешь быть в отряде, где твои сверстники и чуть старше, или чуть младше?",
    "Пожалуйста, закончи фразу: Я приеду в лагерь, потому что...",
    "Я не хочу, чтобы в лагере...",
    "Я боюсь, что в лагере...",
    "Я хочу, чтобы в лагере...",
    "Я хочу, чтобы отряд состоял из ребят, которые…",
    "Мне будет скучно, если в отряде будут заниматься...",
    "Я буду против, если меня заставят...",
    "Я хочу научиться в лагере…",
    "Что ты еще хочешь мне рассказать о себе?",
    "Знаешь ли ты, что в лагерь нельзя брать с собой еду? (Да/Нет)",
    "Знаешь ли ты, что в лагере запрещены телефоны и различные гаджеты? (Да/Нет)",
    "Если родители разрешат, и ты захочешь, то напиши ссылку на свой профиль vk. (необязательный вопрос)",
]

CHILD_SHORT_QUESTIONS: List[str] = [
    "Как тебя зовут (Имя)?",
    "Твоя фамилия?",
    "Сколько тебе лет?",
    "С кем ты хочешь поселиться в одной комнате?",
    "Хочешь ли ты поехать в лагерь? (Да/Нет)",
    "Знаешь ли ты, что в лагерь нельзя брать с собой еду? (Да/Нет)",
    "Знаешь ли ты, что в лагере запрещены телефоны и различные гаджеты? (Да/Нет)",
    "Что ты еще хочешь мне рассказать?",
]

FORMS: Dict[str, Tuple[str, List[str]]] = {
    "parent_full": ("Родительская анкета", PARENT_FULL_QUESTIONS),
    "parent_short": ("Сокращенная родительская", PARENT_SHORT_QUESTIONS),
    "child_full": ("Детская анкета", CHILD_FULL_QUESTIONS),
    "child_short": ("Сокращенная детская", CHILD_SHORT_QUESTIONS),
}


# -----------------------------
# Клавиатуры
# -----------------------------
def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Родительская анкета")],
            [KeyboardButton(text="📝 Сокращенная родительская")],
            [KeyboardButton(text="👦 Детская анкета")],
            [KeyboardButton(text="✏️ Сокращенная детская")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие",
    )


def policy_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, согласен")],
            [KeyboardButton(text="❌ Нет, не согласен")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# -----------------------------
# FSM
# -----------------------------
class Flow(StatesGroup):
    waiting_policy = State()
    filling_form = State()


class AdminFlow(StatesGroup):
    waiting_broadcast = State()


# -----------------------------
# Google Sheets
# -----------------------------
@dataclass
class SheetsClient:
    sheets_id: str
    creds_path: str
    _gc: Optional[gspread.Client] = None
    _sh: Optional[gspread.Spreadsheet] = None

    def connect(self) -> None:
        try:
            creds = Credentials.from_service_account_file(self.creds_path, scopes=SCOPES)
            self._gc = gspread.authorize(creds)
            self._sh = self._gc.open_by_key(self.sheets_id)
            print(f"✓ Подключено к Google Sheets: {self._sh.title}")
        except Exception as e:
            print(f"✗ Ошибка подключения к Google Sheets: {e}")
            raise

    def ensure_worksheet(self, title: str, headers: List[str]) -> None:
        if self._sh is None:
            raise RuntimeError("SheetsClient не подключен")
        
        try:
            ws = self._sh.worksheet(title)
            print(f"✓ Лист '{title}' уже существует")
        except gspread.WorksheetNotFound:
            ws = self._sh.add_worksheet(title=title, rows=2000, cols=max(10, len(headers) + 5))
            print(f"✓ Создан новый лист '{title}'")

        current = ws.row_values(1)
        if current != headers:
            ws.clear()
            ws.append_row(headers, value_input_option="USER_ENTERED")
            print(f"✓ Заголовки обновлены для листа '{title}'")

    def append_row(self, title: str, headers: List[str], row: Dict[str, str]) -> None:
        if self._sh is None:
            raise RuntimeError("SheetsClient не подключен")
        
        try:
            ws = self._sh.worksheet(title)
            data = [row.get(h, "") for h in headers]
            ws.append_row(data, value_input_option="USER_ENTERED")
            print(f"✓ Строка добавлена в лист '{title}'")
        except Exception as e:
            print(f"✗ Ошибка при добавлении строки в '{title}': {e}")
            raise


# -----------------------------
# DB
# -----------------------------
async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                accepted_policy INTEGER DEFAULT 0,
                first_seen TEXT,
                last_seen TEXT
            )
            """
        )
        await db.commit()


async def upsert_user(user_id: int, username: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users(user_id, username, accepted_policy, first_seen, last_seen)
            VALUES(?, ?, COALESCE((SELECT accepted_policy FROM users WHERE user_id=?), 0), ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                last_seen=excluded.last_seen
            """,
            (user_id, username, user_id, now, now),
        )
        await db.commit()


async def set_policy(user_id: int, accepted: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET accepted_policy=? WHERE user_id=?",
            (1 if accepted else 0, user_id),
        )
        await db.commit()


async def get_policy(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT accepted_policy FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0] == 1)


async def all_user_ids() -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE accepted_policy=1") as cur:
            rows = await cur.fetchall()
    return [int(r[0]) for r in rows]


# -----------------------------
# Хелперы
# -----------------------------
def is_yes(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"да", "yes", "y", "ага", "ок", "okay", "окей", "согласен", "согласна", "✅ да, согласен"}


def is_no(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"нет", "no", "n", "не согласен", "не согласна", "❌ нет, не согласен"}


def meta_headers() -> List[str]:
    return ["timestamp_utc", "telegram_user_id", "telegram_username"]


def make_headers(form_key: str) -> List[str]:
    _, questions = FORMS[form_key]
    return meta_headers() + questions


# -----------------------------
# Роутеры
# -----------------------------
router = Router()
admin_router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = message.from_user
    await upsert_user(user.id, user.username or "")

    accepted = await get_policy(user.id)
    if not accepted:
        await state.set_state(Flow.waiting_policy)
        await message.answer(
            "🏕 <b>Добро пожаловать в бот лагеря!</b>\n\n"
            "📄 Для продолжения работы необходимо согласиться с политикой обработки персональных данных.\n\n"
            "Согласны ли вы с нашей политикой обработки персональных данных?",
            reply_markup=policy_kb(),
        )
        return

    await state.clear()
    await message.answer(
        f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
        "📋 Выберите нужную анкету из меню ниже:",
        reply_markup=main_menu_kb()
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    help_text = (
        "ℹ️ <b>Доступные команды:</b>\n\n"
        "/start - Запустить бота и показать главное меню\n"
        "/cancel - Отменить заполнение анкеты\n"
        "/help - Показать эту справку\n\n"
        "📋 <b>Доступные анкеты:</b>\n\n"
        "• Родительская анкета (полная) - 50 вопросов\n"
        "• Сокращенная родительская - 21 вопрос\n"
        "• Детская анкета (полная) - 23 вопроса\n"
        "• Сокращенная детская - 8 вопросов\n\n"
        "💡 <b>Как заполнить анкету:</b>\n"
        "1. Выберите нужную анкету из меню\n"
        "2. Отвечайте на вопросы по очереди\n"
        "3. Если нужно отменить - используйте /cancel\n"
        "4. После завершения данные сохранятся в Google Sheets\n\n"
        "❓ Если возникли вопросы - обратитесь к администратору."
    )
    await message.answer(help_text, reply_markup=main_menu_kb())


@router.message(Flow.waiting_policy)
async def policy_answer(message: Message, state: FSMContext):
    user = message.from_user
    await upsert_user(user.id, user.username or "")

    if is_yes(message.text):
        await set_policy(user.id, True)
        await state.clear()
        await message.answer(
            "✅ <b>Спасибо за согласие!</b>\n\n"
            "Теперь вы можете заполнять анкеты. Выберите нужную из меню:",
            reply_markup=main_menu_kb()
        )
        return

    if is_no(message.text):
        await set_policy(user.id, False)
        await state.set_state(Flow.waiting_policy)
        await message.answer(
            "❌ <b>Без согласия продолжить работу невозможно.</b>\n\n"
            "Если передумаете — нажмите кнопку <b>«Да, согласен»</b> или отправьте команду /start",
            reply_markup=policy_kb()
        )
        return

    await message.answer(
        "⚠️ Пожалуйста, используйте кнопки ниже для ответа:",
        reply_markup=policy_kb()
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "ℹ️ Нет активной анкеты для отмены.",
            reply_markup=main_menu_kb()
        )
        return
    
    await state.clear()
    await message.answer(
        "❌ <b>Заполнение анкеты отменено.</b>\n\n"
        "Вы можете начать заново, выбрав анкету из меню:",
        reply_markup=main_menu_kb()
    )


async def start_form(message: Message, state: FSMContext, form_key: str):
    await state.set_state(Flow.filling_form)
    await state.update_data(form_key=form_key, idx=0, answers={})

    title, questions = FORMS[form_key]
    
    form_icons = {
        "parent_full": "📋",
        "parent_short": "📝",
        "child_full": "👦",
        "child_short": "✏️",
    }
    
    icon = form_icons.get(form_key, "📄")
    
    await message.answer(
        f"{icon} <b>{title}</b>\n\n"
        f"📝 Всего вопросов: {len(questions)}\n\n"
        f"Отвечайте на вопросы по порядку.\n"
        f"Для отмены используйте /cancel\n\n"
        f"Начинаем! 👇",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await asyncio.sleep(0.5)
    await ask_question_by_index(message, state)


async def ask_question_by_index(message: Message, state: FSMContext):
    data = await state.get_data()
    form_key = data["form_key"]
    idx = data["idx"]
    _, questions = FORMS[form_key]

    if idx >= len(questions):
        return

    await message.answer(questions[idx], reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "📋 Родительская анкета")
async def menu_parent_full(message: Message, state: FSMContext):
    await start_form(message, state, "parent_full")


@router.message(F.text == "📝 Сокращенная родительская")
async def menu_parent_short(message: Message, state: FSMContext):
    await start_form(message, state, "parent_short")


@router.message(F.text == "👦 Детская анкета")
async def menu_child_full(message: Message, state: FSMContext):
    await start_form(message, state, "child_full")


@router.message(F.text == "✏️ Сокращенная детская")
async def menu_child_short(message: Message, state: FSMContext):
    await start_form(message, state, "child_short")


@router.message(Flow.filling_form)
async def form_answer(message: Message, state: FSMContext, sheets: SheetsClient):
    data = await state.get_data()
    form_key = data["form_key"]
    idx = data["idx"]
    answers: Dict[str, str] = data["answers"]

    _, questions = FORMS[form_key]

    if idx < len(questions):
        question = questions[idx]
        answers[question] = (message.text or "").strip()

    new_idx = idx + 1

    if new_idx >= len(questions):
        await state.update_data(idx=new_idx, answers=answers)
        await finish_form(message, state, sheets)
        return

    await state.update_data(idx=new_idx, answers=answers)
    await ask_question_by_index(message, state)


async def finish_form(message: Message, state: FSMContext, sheets: SheetsClient):
    data = await state.get_data()
    form_key = data["form_key"]
    form_title, _ = FORMS[form_key]
    answers: Dict[str, str] = data["answers"]

    row: Dict[str, str] = {}
    row["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    row["telegram_user_id"] = str(message.from_user.id)
    row["telegram_username"] = message.from_user.username or ""
    row.update(answers)

    headers = make_headers(form_key)
    
    await message.answer(
        "⏳ <b>Сохраняю анкету...</b>",
        reply_markup=ReplyKeyboardRemove()
    )
    
    try:
        await asyncio.to_thread(sheets.append_row, form_title, headers, row)
        await state.clear()
        await message.answer(
            "✅ <b>Отлично! Анкета успешно сохранена!</b>\n\n"
            "📊 Данные отправлены в Google Sheets\n"
            "🎉 Спасибо за заполнение!\n\n"
            "Вы можете заполнить ещё одну анкету или вернуться в меню:",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        print(f"✗ Ошибка при сохранении анкеты: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка при сохранении анкеты.</b>\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору.",
            reply_markup=main_menu_kb()
        )


# -----------------------------
# Админ: рассылка
# -----------------------------
@admin_router.message(Command("broadcast"))
async def admin_broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.set_state(AdminFlow.waiting_broadcast)
    await message.answer(
        "📢 <b>Режим рассылки</b>\n\n"
        "Отправьте одним сообщением то, что нужно разослать всем пользователям:\n\n"
        "• Текст\n"
        "• Фото с подписью\n"
        "• Фото без подписи\n\n"
        "Для отмены используйте /cancel",
        reply_markup=ReplyKeyboardRemove(),
    )


@admin_router.message(AdminFlow.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return

    user_ids = await all_user_ids()

    if not user_ids:
        await state.clear()
        await message.answer(
            "⚠️ Нет пользователей для рассылки.",
            reply_markup=main_menu_kb()
        )
        return

    text = (message.caption or message.text or "").strip()
    photo_id = message.photo[-1].file_id if message.photo else None

    status_msg = await message.answer(
        f"📤 <b>Начинаю рассылку...</b>\n\n"
        f"👥 Всего пользователей: {len(user_ids)}"
    )

    sent = 0
    failed = 0

    for uid in user_ids:
        try:
            if photo_id:
                await bot.send_photo(chat_id=uid, photo=photo_id, caption=text or None)
            else:
                if not text:
                    continue
                await bot.send_message(chat_id=uid, text=text)
            sent += 1
            await asyncio.sleep(0.035)
        except Exception:
            failed += 1

    await state.clear()
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )
    await message.answer("Вернуться в меню:", reply_markup=main_menu_kb())


# -----------------------------
# Startup
# -----------------------------
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    print("=== Запуск бота ===")
    
    await init_db()
    print("✓ База данных инициализирована")

    sheets = SheetsClient(sheets_id=SHEETS_ID, creds_path=CREDS_PATH)
    sheets.connect()

    for form_key, (title, _) in FORMS.items():
        headers = make_headers(form_key)
        await asyncio.to_thread(sheets.ensure_worksheet, title, headers)

    dispatcher.workflow_data["sheets"] = sheets
    print("✓ Google Sheets настроены")
    print("=== Бот готов к работе ===\n")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty")
    if not SHEETS_ID:
        raise RuntimeError("GOOGLE_SHEETS_ID is empty")
    if not CREDS_PATH:
        raise RuntimeError("GOOGLE_CREDS_PATH is empty")

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(router)
    dp.include_router(admin_router)

    dp.startup.register(on_startup)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
