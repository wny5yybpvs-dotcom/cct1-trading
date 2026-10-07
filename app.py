import streamlit as st
import pandas as pd
import io
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection
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
            return {"USD": 1.0, "RUB": rates.get("RUB", 93.5), "CNY": rates.get("CNY", 7.2)}
    except:
        pass
    return {"USD": 1.0, "RUB": 93.5, "CNY": 7.2}

CURRENCY_RATES = get_exchange_rates()

st.set_page_config(layout="centered", page_title="CCT1 Enterprise Pro")
st.title("🚢 Платформа CCT1 Enterprise v4.5")

# БОКОВАЯ ПАНЕЛЬ СЕТИНГОВ ДЛЯ ПОДКЛЮЧЕНИЙ
st.sidebar.header("⚙️ Настройки интеграций")
sheet_url = st.sidebar.text_input("Ссылка на Google Таблицу:", value="https://docs.google.com/spreadsheets/d/1-0xgXn7iZ-EIr40N_lH9JIXyAIoPuMYWUwS7t7f9_fo/edit?usp=drivesdk")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value="ВАШ_ТОКЕН", type="password")
tg_chat = st.sidebar.text_input("Telegram Chat ID (Группы):", value="ВАШ_ID")

st.sidebar.header("💱 Текущие курсы")
st.sidebar.write(f"💵 1 USD = **{round(CURRENCY_RATES['RUB'], 2)}** RUB")
st.sidebar.write(f"🇨🇳 1 USD = **{round(CURRENCY_RATES['CNY'], 2)}** CNY")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

# ПОДКЛЮЧЕНИЕ ЧТЕНИЯ ИЗ GOOGLE SHEETS
if "://google.com" in sheet_url:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_base = conn.read(spreadsheet=sheet_url, ttl="5s")
    except:
        df_base = pd.DataFrame()
else:
    df_base = pd.DataFrame()

menu_choice = st.selectbox("📌 ПЕРЕКЛЮЧЕНИЕ РАЗДЕЛОВ САЙТА:", ["📥 Ввод данных", "📋 Реестр сделок (Google Sheets)", "📊 Логистический Радар"])

if menu_choice == "📥 Ввод данных":
    st.subheader("📦 Новая сделка")
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    buy_curr = st.selectbox("Валюта закупки товара:", ["USD", "CNY", "RUB"])
    price_buy = st.number_input(f"Сумма закупки ({buy_curr}):", min_value=0.0, value=100000.0)
    
    price_buy_usd = float(price_buy / CURRENCY_RATES.get(buy_curr, 1.0))
    if buy_curr != "USD":
        st.caption(f"ℹ️ В эквиваленте: **${round(price_buy_usd, 2):,} USD**")
        
    price_sell = st.number_input("Цена ПРОДАЖИ товара ($):", min_value=0.0, value=150000.0)
    freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Пошлины и страхование ($):", min_value=0.0, value=3000.0)
    extra_costs = st.number_input("Прочие накладные расходы ($):", min_value=0.0, value=1000.0)
    port_start = st.selectbox("Порт ЗАГРУЗКИ:", sorted(list(helpers.PORTS.keys())), index=4)
    port_end = st.selectbox("Порт РАЗГРУЗКИ:", sorted(list(helpers.PORTS.keys())), index=0)
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    deadline_date = st.date_input("Крайний срок прибытия (Laycan):", value=datetime.now().date() + timedelta(days=5))
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date())

    if st.button("💾 СОХРАНИТЬ В GOOGLE SHEETS И ТЕЛЕГРАМ", type="primary", use_container_width=True):
        if "://google.com" not in sheet_url:
            st.error("❌ Сначала вставьте ссылку на вашу Google Таблицу в левое боковое меню!")
            st.stop()
            
        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        days_in_port = (datetime.now().date() - arrival_date).days
        overdue = max(0, days_in_port - allowed_days)
        demurrage_total = overdue * demurrage_rate
        net_profit = float(price_sell) - price_buy_usd - actual_freight - float(duties) - float(extra_costs) - demurrage_total
        
        new_row = pd.DataFrame([{
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Инкотермс': incoterms, 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 'Цена закупки (вход)': float(price_buy), 'Валюта закупки': buy_curr, 
            'Цена продажи (USD)': float(price_sell), 'Фрахт ($)': float(freight), 'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs), 'Норма простоя (дн)': int(allowed_days), 'Ставка демереджа ($/сут)': float(demurrage_rate), 
            'Крайняя дата прибытия': str(deadline_date), 'Дата захода в порт': str(arrival_date), 'Демередж ($)': float(demurrage_total), 'Чистая прибыль ($)': float(net_profit)
        }])
        
        try:
            updated_df = pd.concat([df_base, new_row], ignore_index=True)
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(spreadsheet=sheet_url, data=updated_df)
            st.success("📊 Сделка вечно сохранена в Google Sheets!")
            
            tg_text = f"📝 *Новая сделка сохранена!*\n\n*ID:* {deal_id}\n*Маршрут:* {port_start} ➡️ {port_end}\n*Прибыль:* ${net_profit:,.2f} USD"
            helpers.send_telegram_message(tg_token, tg_chat, tg_text)
            st.rerun()
        except Exception as e:
            st.error(f"Ошибка записи в Google. Проверьте права 'Редактор' у ссылки таблиц. Ошибка: {str(e)}")

elif menu_choice == "📋 Реестр сделок (Google Sheets)":
    st.subheader("📋 Данные из облака Google Таблиц")
    if df_base.empty:
        st.info("Настройте ссылку на Google Таблицу в левом боковом меню.")
    else:
        st.dataframe(df_base, use_container_width=True)

elif menu_choice == "📊 Логистический Радар":
    st.subheader("📊 Мониторинг положения судна онлайн")
    if df_base.empty:
        st.info("Нет данных. Подключите Google Таблицу со сделками.")
    else:
        selected_deal = st.selectbox("Выберите активную сделку:", list(df_base['ID Сделки'].unique()))
        v_list = df_base[df_base['ID Сделки'] == selected_deal].to_dict('records')
        v_info = v_list[0]
        
        st.write(f"🚢 **Судно:** {v_info['Название судна']} | **Базис:** {v_info.get('Инкотермс', 'CIF')}")
        with st.spinner("Связь со спутниками AIS..."):
            v_lat, v_lon, v_speed, status_text = helpers.get_live_vessel_data(v_info['MMSI/IMO'])
        st.info(f"📡 {status_text}")
        
        port_coords = helpers.PORTS.get(v_info['Порт разгрузки'], {"lat": 44.72, "lon": 37.78})
        distance_to_port = helpers.haversine(v_lat, v_lon, port_coords['lat'], port_coords['lon'])
        st.write(f"📏 **Дистанция до причала разгрузки:** {round(distance_to_port, 1)} км")
        
        if distance_to_port <= 15.0:
            st.error("🎯 Судно находится внутри акватории порта назначения!")
            entry_date = datetime.strptime(str(v_info.get('Дата захода в порт', datetime.now().date())), "%Y-%m-%d").date()
            days_spent = (datetime.now().date() - entry_date).days
            overdue = max(0, days_spent - int(v_info['Норма простоя (дн)']))
            auto_demurrage = overdue * float(v_info['Ставка демереджа ($/сут)'])
            st.error(f"🚨 Начисленный демередж: **${auto_demurrage:,}** (Простой сверх нормы: {overdue} дн.)")
            
            if overdue > 0 and st.button("🚨 ОТПРАВИТЬ СИГНАЛ В TELEGRAM ГРУППУ", use_container_width=True):
                alert_text = f"⚠️ *ВНИМАНИЕ! ДЕМЕРЕДЖ ПОРТА!*\n\n*Сделка:* {selected_deal}\n*Судно:* {v_info['Название судна']}\n*Убыток:* -${auto_demurrage:,}"
                helpers.send_telegram_message(tg_token, tg_chat, alert_text)
                st.success("🚨 Сигнал отправлен в группу команды!")
        else:
            st.success("🌊 Корабль находится на переходе в море.")
            if v_speed > 0.5:
                days_left = distance_to_port / (v_speed * 1.852) / 24
                st.success(f"⏱ **Прогноз прибытия (ETA):** через {round(days_left, 1)} дней ({ (datetime.now() + timedelta(days=days_left)).strftime('%d.%m.%Y') })")

        st.map(pd.DataFrame([{'latitude': float(v_lat), 'longitude': float(v_lon)}, {'latitude': float(port_coords['lat']), 'longitude': float(port_coords['lon'])}]))
