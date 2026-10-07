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

# Функция для загрузки данных
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # Убедимся, что типы данных корректны
        df['Дата'] = pd.to_datetime(df['Дата']).dt.date
        return df
    else:
        # Создаем пустую таблицу с нужными колонками, если файла еще нет
        return pd.DataFrame(columns=[
            'ID Сделки', 'Дата', 'Название судна', 'MMSI/IMO', 
            'Цена закупки ($)', 'Цена продажи ($)', 'Фрахт ($)', 
            'Норма простоя (дн)', 'Ставка демереджа ($/сут)', 
            'Дней простоя сверх нормы', 'Демередж ($)', 'Чистая прибыль ($)'
        ])

# Функция для сохранения данных
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# Загружаем текущую базу данных в сессию
if "df_data" not in st.session_state:
    st.session_state.df_data = load_data()

# --- ИНТЕРФЕЙС САЙТА ---
st.set_page_config(layout="wide", page_title="CCT1 Trading & Logistics")
st.title("🚢 Система управления сделками и логистикой | CCT1")

# Кнопка выхода в боковой панели
if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

# Разделяем интерфейс на Ввод данных и Аналитику
tab1, tab2, tab3 = st.tabs(["📥 Ввод новых данных", "📋 База сделок", "📊 Сводная аналитика"])

# --- ВКЛАДКА 1: ВВОД ДАННЫХ ---
with tab1:
    st.header("Добавить новую сделку / судно")
    
    with st.form("deal_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📦 Параметры сделки")
            deal_id = st.text_input("Номер или ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
            deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
            price_buy = st.number_input("Цена закупки товара ($):", min_value=0.0, step=1000.0, value=100000.0)
            price_sell = st.number_input("Цена продажи товара ($):", min_value=0.0, step=1000.0, value=150000.0)
            freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, step=500.0, value=15000.0)
            
        with col2:
            st.subheader("🚢 Логистика и Демередж")
            vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
            vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
            allowed_days = st.number_input("Нормативное время в порту (дней до демереджа):", min_value=0, value=3)
            demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, step=100.0, value=5000.0)
            days_overdue = st.number_input("Фактический простой сверх нормы (дней):", min_value=0, value=0)

        # Кнопка отправки формы
        submitted = st.form_submit_button("💾 Сохранить сделку в базу")

        
        if submitted:
            # Расчеты
            demurrage_total = days_overdue * demurrage_rate
            net_profit = price_sell - price_buy - freight - demurrage_total
            
            # Новая строка
            new_row = {
                'ID Сделки': deal_id,
                'Дата': deal_date,
                'Название судна': vessel_name,
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
            
            # Добавляем в таблицу и сохраняем
            st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df_data)
            st.success(f"✅ Сделка {deal_id} успешно сохранена!")
            st.rerun()

# --- ВКЛАДКА 2: БАЗА СДЕЛОК ---
with tab2:
    st.header("Все зарегистрированные сделки")
    
    if st.session_state.df_data.empty:
        st.info("База данных пока пуста. Добавьте первую сделку на первой вкладке.")
    else:
        # Показываем интерактивную таблицу
        st.dataframe(st.session_state.df_data, use_container_width=True)
        
        # Возможность удалить сделку
        st.write("---")
        st.subheader("🗑 Удаление сделки")
        delete_id = st.selectbox("Выберите ID сделки для удаления:", st.session_state.df_data['ID Сделки'].unique())
        if st.button("❌ Удалить выбранную сделку"):
            st.session_state.df_data = st.session_state.df_data[st.session_state.df_data['ID Сделки'] != delete_id]
            save_data(st.session_state.df_data)
            st.warning(f"Сделка {delete_id} удалена.")
            st.rerun()

# --- ВКЛАДКА 3: АНАЛИТИКА И КАРТА ---
with tab3:
    st.header("📈 Финансовые итоги и Логистика")
    
    if st.session_state.df_data.empty:
        st.info("Нет данных для отображения аналитики.")
    else:
        df = st.session_state.df_data
        
        # Общие метрики по всему бизнесу
        m1, m2, m3 = st.columns(3)
        m1.metric("Всего сделок", len(df))
        m2.metric("Общий начисленный демередж", f"${df['Демередж ($)'].sum():,}")
        m3.metric("ОБЩАЯ ЧИСТАЯ ПРИБЫЛЬ", f"${df['Чистая прибыль ($)'].sum():,}")
        
        # График прибыли по сделкам
        st.write("### Прибыль в разрезе сделок")
        st.bar_chart(df.set_index('ID Сделки')['Чистая прибыль ($)'])
        
        # Интерактивная карта для отслеживания выбранного судна
        st.write("---")
        st.subheader("📍 Мониторинг положения судна")
        
        selected_deal = st.selectbox("Выберите сделку для проверки судна на карте:", df['ID Сделки'].unique())
        vessel_info = df[df['ID Сделки'] == selected_deal].iloc[0]
        
        st.write(f"**Судно:** {vessel_info['Название судна']} | **MMSI:** {vessel_info['MMSI/IMO']}")
        
        # Координаты по умолчанию (например, Суэцкий канал для демонстрации трейдинга)
        # На следующем этапе мы заменим эти цифры на автоматический парсинг по MMSI
        lat, lon = 29.93, 32.55 
        
        # Строим карту Folium (она отлично масштабируется на смартфонах)
        m = folium.Map(location=[lat, lon], zoom_start=6)
        folium.Marker(
            [lat, lon], 
            popup=f"Судно: {vessel_info['Название судна']}", 
            tooltip=vessel_info['Название судна'],
            icon=folium.Icon(color='blue', icon='ship', prefix='fa')
        ).add_to(m)
        
        st_folium(m, width=700, height=400, returned_objects=[])
