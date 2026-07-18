"""
Бот обучения новых сотрудников сети кафе-ресторанов "Капучино"
Должность: Продавец
Запуск: python bot.py
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)

from config import BOT_TOKEN, ADMIN_CHAT_ID, BRANCHES

# ── Логирование ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Инициализация ─────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ── Состояния FSM ─────────────────────────────────────────────────────────────
class Registration(StatesGroup):
    agreement   = State()   # Пользовательское соглашение
    full_name   = State()   # ФИО
    branch      = State()   # Подразделение
    phone       = State()   # Номер телефона
    consent     = State()   # Подтверждение данных
    confirmed   = State()   # Анкета подтверждена


# ── Клавиатуры ────────────────────────────────────────────────────────────────
def kb(*labels, resize=True, one_time=True):
    buttons = [[KeyboardButton(text=t)] for t in labels]
    return ReplyKeyboardMarkup(keyboard=buttons,
                               resize_keyboard=resize,
                               one_time_keyboard=one_time)

def kb_phone():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона",
                                  request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )

def kb_branches():
    buttons = [[KeyboardButton(text=b)] for b in BRANCHES]
    return ReplyKeyboardMarkup(keyboard=buttons,
                               resize_keyboard=True,
                               one_time_keyboard=True)

KB_AGREEMENT = kb("✅ Принимаю соглашение", "❌ Не принимаю")
KB_CONSENT   = kb("✅ Подтверждаю", "◀️ Изменить данные")
KB_BACK      = kb("🔄 Начать заново")
KB_MAIN      = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Начать обучение")],
        [KeyboardButton(text="👤 Моя карточка")],
    ],
    resize_keyboard=True,
)

# ── Текст пользовательского соглашения ───────────────────────────────────────
AGREEMENT_TEXT = (
    "📄 Для продолжения необходимо ознакомиться с условиями обработки персональных данных.\n\n"
    "👉 <a href=\"https://sewewr.github.io/kapuchino-privacy.html\">Пользовательское соглашение</a>\n\n"
    "Нажимая «Принимаю соглашение», вы подтверждаете своё согласие на обработку "
    "персональных данных в соответствии с ФЗ №152-ФЗ."
)


# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в систему обучения сети кафе-ресторанов <b>«Капучино»</b>!\n\n"
        "Здесь вы пройдёте обучение по вашей должности и подготовитесь к первому рабочему дню.\n\n"
        "Перед началом необходимо ознакомиться с пользовательским соглашением 👇",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    await asyncio.sleep(0.5)
    await message.answer(
        AGREEMENT_TEXT,
        parse_mode="HTML",
        reply_markup=KB_AGREEMENT,
    )
    await state.set_state(Registration.agreement)


# ── ШАГ 0: СОГЛАШЕНИЕ ────────────────────────────────────────────────────────
@dp.message(Registration.agreement, F.text == "✅ Принимаю соглашение")
async def agreement_accepted(message: Message, state: FSMContext):
    await state.update_data(agreement_accepted=True,
                            agreement_date=datetime.now().strftime("%d.%m.%Y %H:%M"))
    await state.set_state(Registration.full_name)
    await message.answer(
        "✅ Соглашение принято.\n\n"
        "Теперь заполним анкету — это займёт около 1 минуты.\n\n"
        "Введите ваше <b>ФИО</b> полностью:\n"
        "<i>Например: Иванов Иван Иванович</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Registration.agreement, F.text == "❌ Не принимаю")
async def agreement_declined(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вы отказались от принятия соглашения.\n\n"
        "Без согласия на обработку персональных данных "
        "продолжить регистрацию невозможно.\n\n"
        "Если вы передумаете — нажмите /start для повторного запуска.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Registration.agreement)
async def agreement_unknown(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, воспользуйтесь кнопками ниже 👇",
        reply_markup=KB_AGREEMENT,
    )


# ── ШАГ 1: ФИО ────────────────────────────────────────────────────────────────
@dp.message(Registration.full_name)
async def get_full_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if len(name.split()) < 2:
        await message.answer(
            "Пожалуйста, введите <b>полное ФИО</b> — Фамилию, Имя и Отчество.\n"
            "<i>Например: Иванов Иван Иванович</i>",
            parse_mode="HTML",
        )
        return

    allowed = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ -")
    if not all(c in allowed for c in name):
        await message.answer(
            "ФИО должно содержать только буквы. Попробуйте ещё раз:",
        )
        return

    await state.update_data(full_name=name)
    await state.set_state(Registration.branch)
    await message.answer(
        f"Отлично, <b>{name.split()[1]}</b>! 👍\n\n"
        "Выберите ваше <b>подразделение</b>:",
        parse_mode="HTML",
        reply_markup=kb_branches(),
    )


# ── ШАГ 2: ПОДРАЗДЕЛЕНИЕ ─────────────────────────────────────────────────────
@dp.message(Registration.branch)
async def get_branch(message: Message, state: FSMContext):
    branch = message.text.strip()

    if branch not in BRANCHES:
        await message.answer(
            "Пожалуйста, выберите подразделение из списка ниже 👇",
            reply_markup=kb_branches(),
        )
        return

    await state.update_data(branch=branch)
    await state.set_state(Registration.phone)
    await message.answer(
        "Укажите ваш <b>номер телефона</b>.\n"
        "Нажмите кнопку ниже или введите вручную в формате <i>+7XXXXXXXXXX</i>:",
        parse_mode="HTML",
        reply_markup=kb_phone(),
    )


# ── ШАГ 3: ТЕЛЕФОН ───────────────────────────────────────────────────────────
@dp.message(Registration.phone, F.contact)
async def phone_from_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await show_consent(message, state)


@dp.message(Registration.phone)
async def phone_manual(message: Message, state: FSMContext):
    phone = message.text.strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer(
            "Пожалуйста, введите корректный номер телефона.\n"
            "<i>Например: +79001234567</i>",
            parse_mode="HTML",
            reply_markup=kb_phone(),
        )
        return
    await state.update_data(phone=phone)
    await show_consent(message, state)


# ── ШАГ 4: ПОДТВЕРЖДЕНИЕ ДАННЫХ ──────────────────────────────────────────────
async def show_consent(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(Registration.consent)

    text = (
        "📋 <b>Проверьте данные анкеты:</b>\n\n"
        f"👤 <b>ФИО:</b> {data.get('full_name')}\n"
        f"🏪 <b>Подразделение:</b> {data.get('branch')}\n"
        f"📱 <b>Телефон:</b> {data.get('phone')}\n\n"
        "Всё верно?"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=KB_CONSENT)


@dp.message(Registration.consent, F.text == "◀️ Изменить данные")
async def consent_back(message: Message, state: FSMContext):
    await state.clear()
    await cmd_start(message, state)


@dp.message(Registration.consent, F.text == "✅ Подтверждаю")
async def consent_ok(message: Message, state: FSMContext):
    data = await state.get_data()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    await state.update_data(registered_at=now)
    await state.set_state(Registration.confirmed)

    await message.answer(
        "✅ <b>Анкета успешно заполнена!</b>\n\n"
        f"Добро пожаловать в команду <b>«Капучино»</b>, "
        f"{data['full_name'].split()[1]}! 🎉\n\n"
        "Теперь вы можете приступить к обучению. "
        "Программа состоит из нескольких модулей — "
        "каждый включает материалы для изучения и тест для проверки знаний.\n\n"
        "Нажмите кнопку ниже, чтобы начать 👇",
        parse_mode="HTML",
        reply_markup=KB_MAIN,
    )

    await notify_admin(data, message.from_user, now)


# ── ГЛАВНОЕ МЕНЮ ─────────────────────────────────────────────────────────────
@dp.message(Registration.confirmed, F.text == "📚 Начать обучение")
async def start_training(message: Message, state: FSMContext):
    data = await state.get_data()
    branch = data.get('branch', 'вашей должности')
    await message.answer(
        f"📚 <b>Программа обучения — {branch}</b>\n\n"
        "Модули будут добавляться по мере готовности материалов.\n\n"
        "⏳ <i>Скоро здесь появятся уроки — следите за обновлениями!</i>",
        parse_mode="HTML",
        reply_markup=KB_MAIN,
    )


@dp.message(Registration.confirmed, F.text == "👤 Моя карточка")
async def my_card(message: Message, state: FSMContext):
    data = await state.get_data()
    text = (
        "👤 <b>Ваша карточка сотрудника</b>\n\n"
        f"📝 <b>ФИО:</b> {data.get('full_name', '—')}\n"
        f"🏪 <b>Подразделение:</b> {data.get('branch', '—')}\n"
        f"📱 <b>Телефон:</b> {data.get('phone', '—')}\n"
        f"📅 <b>Дата регистрации:</b> {data.get('registered_at', '—')}\n"
        f"📄 <b>Соглашение принято:</b> {data.get('agreement_date', '—')}\n"
        f"📊 <b>Статус:</b> Проходит обучение\n"
        f"🎓 <b>Должность:</b> {data.get('branch', '—')}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=KB_MAIN)


# ── Команда /delete ───────────────────────────────────────────────────────────
@dp.message(F.text == "/delete")
async def delete_data(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🗑 Ваши данные удалены из системы.\n\n"
        "Если вы хотите зарегистрироваться заново — нажмите /start",
        reply_markup=ReplyKeyboardRemove(),
    )
    # Уведомляем администратора об удалении
    if ADMIN_CHAT_ID:
        try:
            tg = f"@{message.from_user.username}" if message.from_user.username else f"id:{message.from_user.id}"
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"🗑 Пользователь {tg} запросил удаление своих данных.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления об удалении: {e}")


# ── «Начать заново» ───────────────────────────────────────────────────────────
@dp.message(F.text == "🔄 Начать заново")
async def restart(message: Message, state: FSMContext):
    await cmd_start(message, state)


# ── УВЕДОМЛЕНИЕ РУКОВОДИТЕЛЮ ─────────────────────────────────────────────────
async def notify_admin(data: dict, user, registered_at: str):
    if not ADMIN_CHAT_ID:
        return

    tg_username = f"@{user.username}" if user.username else f"id:{user.id}"

    text = (
        "🆕 <b>Новый сотрудник зарегистрировался!</b>\n\n"
        f"👤 <b>ФИО:</b> {data.get('full_name', '—')}\n"
        f"🏪 <b>Подразделение:</b> {data.get('branch', '—')}\n"
        f"📱 <b>Телефон:</b> {data.get('phone', '—')}\n"
        f"✈️ <b>Telegram:</b> {tg_username}\n"
        f"📅 <b>Дата регистрации:</b> {registered_at}\n"
        f"📄 <b>Соглашение принято:</b> {data.get('agreement_date', '—')}\n"
        f"🎓 <b>Должность:</b> {data.get('branch', '—')}\n"
        f"📊 <b>Статус:</b> Приступил к обучению"
    )
    try:
        await bot.send_message(ADMIN_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление администратору: {e}")


# ── ЗАПУСК ────────────────────────────────────────────────────────────────────
async def main():
    logger.info("Бот «Капучино» запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
