import streamlit as st
import pandas as pd
import requests

# Инициализация приватности
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Вход в систему трейдинга CCT1")
    pwd = st.text_input("Введите пароль компании:", type="password")
    if st.button("Войти"):
        if pwd == "cct1_trade":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Неверный пароль")
    st.stop()

# --- ОСНОВНОЙ ИНТЕРФЕЙС ТРЕЙДЕРА ---
st.set_page_config(layout="wide", page_title="CCT1 Trading & Logistics")
st.title("🚢 Панель трейдинга и аналитики демереджа | CCT1")

# 1. Форма добавления/обновления сделки
st.sidebar.header("📥 Управление сделками")
deal_id = st.sidebar.text_input("Номер сделки (ID):", "DEAL-2026-01")
vessel_mmsi = st.sidebar.text_input("MMSI / IMO Судна (для трекинга):", "211281610") # Пример MMSI

col1, col2, col3 = st.sidebar.columns(3)
price_buy = col1.number_input("Цена закупки, $", value=500000)
price_sell = col2.number_input("Цена продажи, $", value=680000)
freight_base = col3.number_input("Базовый фрахт, $", value=40000)

allowed_days = st.sidebar.number_input("Нормативное время в порту (до демереджа), дн:", value=3)
demurrage_rate = st.sidebar.number_input("Ставка демереджа ($ / сутки):", value=15000)
days_overdue = st.sidebar.number_input("Фактический простоя сверх нормы (дней):", value=2) # Можно автоматизировать через API

# 2. Логика расчетов
demurrage_total = days_overdue * demurrage_rate
gross_profit = price_sell - price_buy - freight_base
net_profit = gross_profit - demurrage_total

# 3. Главный экран аналитики
st.header(f"Анализ сделки: {deal_id}")

# Визуальные карточки (Метрики)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Грязная прибыль (до демереджа)", f"${gross_profit:,}")
m2.metric("Начисленный демередж ⚠️", f"${demurrage_total:,}", delta=f"+${demurrage_rate} / день", delta_color="inverse")
m3.metric("ЧИСТАЯ ПРИБЫЛЬ СДЕЛКИ", f"${net_profit:,}")
m4.metric("Рентабельность (ROI)", f"{round((net_profit / price_buy) * 100, 1)}%")

# 4. Блок логистики и карты (Имитация получения данных с судна)
st.write("---")
st.header("📍 Мониторинг положения судна и логистика")

# В реальном приложении здесь будет запрос к API (например, VesselAPI или AisStream)
# Ниже пример симуляции координат судна у причала
vessel_lat = 55.75  # Замените на реальные координаты из API
vessel_lon = 37.61

st.write(f"**Статус судна (MMSI: {vessel_mmsi}):** Стоит на рейде / Ожидает разгрузки")

# Отображение судна на карте
map_data = pd.DataFrame({'lat': [vessel_lat], 'lon': [vessel_lon]})
st.map(map_data, zoom=10)

# Вкладка логов
st.info(f"Судно зашло в зону контроля порта. Идет {allowed_days + days_overdue} день нахождения в порту. Лимит превышен на {days_overdue} дн.")
