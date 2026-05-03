import streamlit as st
from typing import Any

TRANSLATIONS = {
    "Ru": {
        # Боковая панель (Sidebar)
        "settings": "Настройки",
        "coupon_type_label": "Тип купона:",
        "floater": "Флоатер",
        "fix": "Фикс",
        "bond_label": "Облигация:",
        'placeholder': 'ОФЗ .....',
        'language': 'Язык:',

        # Заголовки и основной контент
        "main_title": "Карта доходности ОФЗ 🧠",
        "bond_name": "ОФЗ",  # Для подзаголовка перед номером

        # Метрики (Карточки)
        "yield": "Доходность, %",
        "price": "Цена, %",
        "coupon_val": "Купон, %",
        "next_coupon": "Дата следующего купона",
        "duration": "Дюрация, годы",
        "aci": "НКД, ₽",  # Accrued Coupon Interest
        "frequency": "Периодичность выплат, дни",
        "maturity_date": "Дата погашения",
        "spread_format": "б.п. к {benchmark}",

        # Инфо-сообщения
        "click_hint": "Для вывода подробной информации нажмите на точку или выберите выпуск в списке",
        'error_msg': 'Не удалось загрузить данные',
        'bond_info_warning': 'Не удалось загрузить информацию о выбранной облигации, возможно, она недоступна',

        # Chart elements
        "zcyc": "КБД",
        "to_maturity": "До погашения",
        "value": "Значение",
        "years_label": "лет",
        "eff_yield": "Эффективная доходность",
        "duration_label": "Дюрация"
    },
    "En": {
        # Sidebar
        "settings": "Settings",
        "coupon_type_label": "Coupon Type:",
        "floater": "Floating",
        "fix": "Fixed",
        "bond_label": "Bond:",
        'placeholder': 'OFZ .....',
        'language': 'Language:',

        # Main Content
        "main_title": "OFZ Yield Dashboard 🧠",
        "bond_name": "OFZ",

        # Metrics
        "yield": "Yield, %",
        "price": "Price, %",
        "coupon_val": "Coupon, %",
        "next_coupon": "Next Coupon Date",
        "duration": "Duration, years",
        "aci": "ACI, ₽",
        "frequency": "Payment Frequency, days",
        "maturity_date": "Maturity Date",
        "spread_format": "bps to {benchmark}",

        # Info
        "click_hint": "Click a data point or select an issue from the list for details",
        'error_msg': 'Unable to load data',
        'bond_info_warning': 'Bond details unavailable: this bond could not be found or is no longer active',

        # Chart elements
        "zcyc": "G-Curve", # Zero-Coupon Yield Curve
        "to_maturity": "To maturity",
        "value": "Value",
        "years_label": "years",
        "eff_yield": "Effective yield",
        "duration_label": "Duration"
    }
}


def translate(key: str, **kwargs: Any) -> str:

    """
    Translate UI text based on current language stored in session state.

    Args:
        key (str): Translation key used to lookup text in TRANSLATIONS.
        **kwargs: Optional formatting variables for dynamic text.

    Returns:
        str: Translated and formatted string. Falls back to `key` if translation is missing.

    """

    # Get current language (default to Russian if not set)
    lang = st.session_state.get("lang", "Ru")

    # Lookup translation in dictionary:
    # TRANSLATIONS structure → {lang: {key: text}}
    # Fallback to `key` if translation is not found
    text = TRANSLATIONS.get(lang, {}).get(key, key)

    # Apply string formatting if variables are provided
    # Example: translate("spread_format", benchmark="RUSFAR") → "bps to RUSFAR"
    if kwargs:
        return text.format(**kwargs)
    return text
