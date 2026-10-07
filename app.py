import streamlit as st
import pandas as pd
import os
from datetime import datetime
import folium
from streamlit_folium import st_folium

# --- НАСТРОЙКА БЕЗОПАСНОСТИ ---
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

# --- ПУТЬ К ФАЙЛУ ХРАНЕНИЯ ДАННЫХ ---
DATA_FILE = "trading_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except:
            pass
    return pd.DataFrame(columns=[
        'ID Сделки', 'Дата', 'Название sudna', 'MMSI/IMO', 
        'Цена закупки ($)', 'Цена продажи ($)', 'Фрахт ($)', 
        'Норма простоя (дн)', 'Ставка демереджа ($/сут)', 
        'Дней простоя сверх нормы', 'Демередж ($)', 'Чистая прибыль ($)'
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

if "df_data" not in st.session_state:
    st.session_state.df_data = load_data()

# --- ИНТЕРФЕЙС САЙТА ---
st.set_page_config(layout="centered", page_title="CCT1 Trading & Logistics")
st.title("🚢 Система CCT1")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

# ТРИ ВКЛАДКИ ДЛЯ МОБИЛЬНОЙ ВЕРСИИ
tab1, tab2, tab3 = st.tabs(["📥 Ввод данных", "📋 База сделок", "📊 Аналитика"])

# --- ВКЛАДКА 1: ВВОД ДАННЫХ ---
with tab1:
    st.subheader("📦 Параметры сделки")
    deal_id = st.text_input("Номер или ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    price_buy = st.number_input("Цена закупки товара ($):", min_value=0.0, step=1000.0, value=100000.0)
    price_sell = st.number_input("Цена продажи товара ($):", min_value=0.0, step=1000.0, value=150000.0)
    freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, step=500.0, value=15000.0)
        
    st.subheader("🚢 Логистика и Демередж")
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=0, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, step=100.0, value=5000.0)
    days_overdue = st.number_input("Фактический простой сверх нормы (дней):", min_value=0, value=0)

    st.write("---")
    
    if st.button("💾 СОХРАНИТЬ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        demurrage_total = days_overdue * demurrage_rate
        net_profit = price_sell - price_buy - freight - demurrage_total
        
        new_row = {
            'ID Сделки': deal_id,
            'Дата': str(deal_date),
            'Название sudna': vessel_name,
            'MMSI/IMO': vessel_mmsi,
            'Цена закупки ($)': price_buy,
            'Цена продажи ($)': price_sell,
            'Фрахт ($)': freight,
            'Норма простоя (дн)': allowed_days,
            'Ставка демереджа ($/сут)': demurrage_rate,
            'Дней простоя сверх нормы': days_overdue,
            'Демередж ($)': demurrage_total,
            'Чистая прибыль ($)': net_profit
        }
        
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        save_data(st.session_state.df_data)
        st.success(f"✅ Сделка {deal_id} сохранена!")
        st.rerun()

# --- ВКЛАДКА 2: БАЗА СДЕЛОК ---
with tab2:
    st.header("Все зарегистрированные сделки")
    if st.session_state.df_data.empty:
        st.info("База данных пока пуста.")
    else:
        st.dataframe(st.session_state.df_data, use_container_width=True)
        st.write("---")
        delete_id = st.selectbox("ID для удаления:", st.session_state.df_data['ID Сделки'].unique())
        if st.button("❌ Удалить сделку", use_container_width=True):
            st.session_state.df_data = st.session_state.df_data[st.session_state.df_data['ID Сделки'] != delete_id]
            save_data(st.session_state.df_data)
            st.warning(f"Сделка {delete_id} удалена.")
            st.rerun()

# --- ВКЛАДКА 3: АНАЛИТИКА И КАРТА ---
with tab3:
    st.header("📈 Финансовые итоги")
    if st.session_state.df_data.empty:
        st.info("Нет данных для отображения аналитики.")
    else:
        df = st.session_state.df_data
        
        st.metric("Всего сделок", len(df))
        st.metric("Общий демередж", f"${pd.to_numeric(df['Демередж ($)']).sum():,}")
        st.metric("ОБЩАЯ ЧИСТАЯ ПРИБЫЛЬ", f"${pd.to_numeric(df['Чистая прибыль ($)']).sum():,}")
        
        st.write("### Прибыль по сделкам")
        chart_data = df.set_index('ID Сделки')['Чистая прибыль ($)'].astype(float)
        st.bar_chart(chart_data)
        
        st.write("---")
        st.subheader("📍 Положение судна")
        selected_deal = st.selectbox("Сделка для проверки карты:", df['ID Сделки'].unique())
        vessel_info = df[df['ID Сделки'] == selected_deal].iloc[0]
        
        st.write(f"**Судно:** {vessel_info['Название sudna']} | **MMSI:** {vessel_info['MMSI/IMO']}")
        
        lat, lon = 29.93, 32.55
        m = folium.Map(location=[lat, lon], zoom_start=6)
        folium.Marker([lat, lon], popup=str(vessel_info['Название sudna'])).add_to(m)
        st_folium(m, width=320, height=300, returned_objects=[])
