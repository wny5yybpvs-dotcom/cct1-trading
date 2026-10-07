import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import helpers

COMPANY_PASSWORD = "cct1_trade"

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Вход в систему трейдинга CCT1")
    pwd = st.text_input("Введите пароль компании:", type="password")
    if st.button("Войти"):
        if pwd == COMPANY_PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("❌ Неверный пароль")
    st.stop()

@st.cache_data(ttl=3600)
def get_exchange_rates():
    try:
        r = requests.get("https://er-api.com", timeout=5)
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            return {"USD": 1.0, "RUB": rates.get("RUB", 95.0), "CNY": rates.get("CNY", 7.3)}
    except:
        pass
    return {"USD": 1.0, "RUB": 95.0, "CNY": 7.3}

CURRENCY_RATES = get_exchange_rates()

# Жесткий сброс сессии при несовпадении ключевых трейдинг-колонок зерна
if "df_data" not in st.session_state or "Влажность (%)" not in st.session_state.df_data.columns:
    st.session_state.df_data = pd.DataFrame([{
        'ID Сделки': 'DEAL-TEST-GRAIN', 'Дата': str(datetime.now().date()), 'Статус рейса': 'В порту', 'Инкотермс': 'CIF',
        'Объем (Тонн)': 5000.0, 'Название судна': 'Vessel Alpha', 'MMSI/IMO': '211281610',
        'Порт загрузки': 'Стамбул', 'Порт разгрузки': 'Новороссийск', 
        'Цена закупки (вход)': 700000.0, 'Валюта закупки': 'CNY', 'Цена продажи (USD)': 180000.0, 
        'Фрахт ($)': 15000.0, 'Экспортная пошлина ($)': 0.0, 'Прочие расходы ($)': 2000.0, 
        'Норма выгрузки (т/сут)': 1500.0, 'Ставка демереджа ($/сут)': 5000.0,
        'Крайняя дата прибытия': str(datetime.now().date() + timedelta(days=2)), 
        'Дата захода в порт': str(datetime.now().date() - timedelta(days=6)),
        'Влажность (%)': 14.5, 'Сорная примесь (%)': 2.5,
        'Рефакция веса (Тонн)': 50.0, 'Объем выгрузки (Тонн)': 4950.0,
        'Паритет закупки CPT ($/т)': 110.5, 'Демередж ($)': 13333.33, 'Чистая прибыль ($)': 45000.0, 'Прибыль/Тонна ($)': 9.0
    }])

st.set_page_config(layout="wide", page_title="CCT1 Enterprise")
st.title("🚢 Платформа CCT1 Global Tracker")

st.sidebar.header("💱 Живой курс валют")
st.sidebar.write(f"💵 1 USD = **{round(CURRENCY_RATES['RUB'], 2)}** RUB")
st.sidebar.write(f"🇨🇳 1 USD = **{round(CURRENCY_RATES['CNY'], 2)}** CNY")

st.sidebar.header("🤖 Настройки Telegram")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value="ВАШ_ТОКЕН", type="password")
tg_chat = st.sidebar.text_input("Telegram Chat ID:", value="ВАШ_ID")

menu_choice = st.selectbox("📌 ПЕРЕКЛЮЧЕНИЕ РАЗДЕЛОВ САЙТА:", ["📥 Ввод данных", "📋 Реестр сделок (Excel)", "📊 Логистический Радар"])

if menu_choice == "📥 Ввод данных":
    helpers.render_input_tab(CURRENCY_RATES, tg_token, tg_chat)
elif menu_choice == "📋 Реестр сделок (Excel)":
    helpers.render_excel_tab()
elif menu_choice == "📊 Логистический Радар":
    helpers.render_radar_tab(tg_token, tg_chat)
