import streamlit as st
import pandas as pd
import io
import datetime

def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("📥 Ввод сделки & Трейдинг-Калькулятор")
    
    today_dt = datetime.date.today()
    
    col1, col2 = st.columns(2)
    with col1:
        deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}")
        vessel_status = st.selectbox("🚦 Статус рейса:", ["В порту", "В пути", "Завершена (Архив)"])
        incoterms = st.selectbox("Базис поставки:", ["CIF", "CFR", "FOB"])
        cargo_volume = st.number_input("Объем погрузки (Брутто Тонн):", min_value=1.0, value=5000.0, step=100.0)
    with col2:
        deal_date = st.date_input("Дата сделки:", value=today_dt)
        vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
        port_start = st.text_input("Порт ЗАГРУЗКИ:", value="Стамбул")
        port_end = st.text_input("Порт РАЗГРУЗКИ:", value="Новороссийск")

    st.subheader("🌾 Коммерческие параметры качества (Рефакция)")
    col3, col4 = st.columns(2)
    with col3:
        moisture = st.number_input("Влажность фактическая (%)", min_value=0.0, max_value=30.0, value=14.5, step=0.1)
    with col4:
        admixture = st.number_input("Сорная примесь фактическая (%)", min_value=0.0, max_value=20.0, value=2.5, step=0.1)

    st.subheader("🚢 Параметры Чартера & Расчет Laytime")
    col7, col8 = st.columns(2)
    with col7:
        op_type = st.selectbox("Тип операции для расчета сталии:", ["Выгрузка", "Погрузка"])
        rate_per_day = st.number_input("Контрактная суточная норма обработки (Тонн/сут):", min_value=1.0, value=1500.0)
        laytime_terms = st.selectbox("Условия учета выходных:", ["SHEX (Вых. исключены)", "SHINC (Вых. включены)"])
    with col8:
        demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
        arrival_date = st.date_input("Дата фактического захода в порт:", value=today_dt - datetime.timedelta(days=8))

    st.subheader("💵 Экономика Трейда & Скрытые Расходы")
    col5, col6 = st.columns(2)
    with col5:
        buy_curr = st.selectbox("Валюта закупки:", ["USD", "CNY", "RUB"])
        price_buy_total = st.number_input(f"Стоимость закупки партии груза ({buy_curr}):", min_value=0.0, value=700000.0)
        price_sell_total = st.number_input("Цена продажи партии ($ USD):", min_value=0.0, value=180000.0)
    with col6:
        freight = st.number_input("Базовый фрахт судна ($):", min_value=0.0, value=15000.0)
        extra_costs = st.number_input("Прочие накладные портовые расходы ($):", min_value=0.0, value=2000.0)
        survey_costs = st.number_input("Сюрвейерский контроль品質 (SGS/анализы) ($):", min_value=0.0, value=500.0)
        bank_commission = st.number_input("Банковские комиссии и Аккредитив L/C ($):", min_value=0.0, value=1200.0)
        target_margin = st.number_input("Целевая маржа трейдера ($ / т):", min_value=0.0, value=10.0)

    if st.button("💾 ЗАФИКСИРОВАТЬ СДЕЛКУ И РАССЧИТАТЬ МАРЖУ", type="primary", use_container_width=True):
        # Математика 1: Коммерческая рефакция веса
        m_loss = float(max(0.0, (moisture - 14.0) / 100.0) * cargo_volume)
        a_loss = float(max(0.0, (admixture - 2.0) / 100.0) * cargo_volume)
        total_refaction = float(m_loss + a_loss)
        delivered_volume = float(cargo_volume - total_refaction)

        # Математика 2: Профессиональный расчет Паритета цены закупки CPT (Netback)
        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        total_overhead = actual_freight + float(extra_costs) + float(survey_costs) + float(bank_commission)
        available_for_grain = float(price_sell_total) - total_overhead - (target_margin * cargo_volume)
        netback_cpt_usd = available_for_grain / cargo_volume

        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Статус рейса': vessel_status, 'Инкотермс': incoterms,
            'Объем (Тонн)': cargo_volume, 'Название судна': vessel_name, 'MMSI/IMO': "211281610",
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 
            'Цена закупки (вход)': price_buy_total, 'Валюта закупки': buy_curr, 'Цена продажи (USD)': price_sell_total, 
            'Фрахт ($)': actual_freight, 'Экспортная пошлина ($)': 0.0, 'Прочие расходы ($)': float(extra_costs), 
            'Сюрвей и анализы ($)': float(survey_costs), 'Банковская комиссия L/C ($)': float(bank_commission),
            'Тип операции сталии': op_type, 'Норма обработки (т/сут)': rate_per_day, 'Условия сталии (SHEX/SHINC)': laytime_terms,
            'Ставка демереджа ($/сут)': float(demurrage_rate), 'Дата захода в порт': str(arrival_date),
            'Влажность (%)': moisture, 'Сорная примесь (%)': admixture,
            'Рефакция веса (Тонн)': round(total_refaction, 1), 'Объем выгрузки (Тонн)': round(delivered_volume, 1),
            'Паритет закупки CPT ($/т)': round(netback_cpt_usd, 2),
            'Демередж ($)': 0.0, 'Диспач ($)': 0.0, 'Чистая прибыль ($)': 0.0, 'Прибыль/Тонна ($)': 0.0
        }
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"✅ Сделка зернотрейдера {deal_id} успешно рассчитана и внесена!")
        st.rerun()

def render_excel_tab():
    st.subheader("📋 Экономический реестр зерновых контрактов")
    current_today = datetime.date.today()
    
    updated_rows = []
    for row in st.session_state.df_data.to_dict('records'):
        cargo = float(row.get('Объем (Тонн)', 5000.0))
        rate = float(row.get('Норма обработки (т/сут)', 1500.0))
        allowed_days = cargo / max(1.0, rate)
        row['Разрешенное сталийное время (дн)'] = round(allowed_days, 2)
        
        try:
            arr_dt = datetime.datetime.strptime(str(row.get('Дата захода в порт', current_today)), "%Y-%m-%d").date()
            calendar_days = (current_today - arr_dt).days
        except:
            calendar_days = 0
            
        row['Фактически в порту (календарных дн)'] = calendar_days
        
        # Математика сталии: Срезаем воскресенья при условиях SHEX
        working_days = float(calendar_days)
        if "SHEX" in row.get('Условия сталии (SHEX/SHINC)', 'SHEX'):
            try:
                for d in range(calendar_days):
                    check_date = arr_dt + datetime.timedelta(days=d)
                    if check_date.weekday() == 6:  # 6 = Воскресенье
                        working_days -= 1.0
            except:
                pass
        row['Рабочих дней простоя'] = working_days
        
        # Математический расчет Демереджа / Диспача
        dem_rate = float(row.get('Ставка демереджа ($/сут)', 0.0))
        if working_days > allowed_days:
            row['Демередж ($)'] = round((working_days - allowed_days) * dem_rate, 2)
            row['Диспач ($)'] = 0.0
        else:
            row['Демередж ($)'] = 0.0
            row['Диспач ($)'] = round((allowed_days - working_days) * (dem_rate / 2.0), 2)
            
        buy_curr = row.get('Валюта закупки', 'CNY')
        curr_rate = 7.3 if buy_curr == 'CNY' else (95.0 if buy_curr == 'RUB' else 1.0)
        buy_usd = float(row.get('Цена закупки (вход)', 0.0)) / curr_rate
        fr = 0.0 if row.get('Инкотермс') == "FOB" else float(row.get('Фрахт ($)', 0.0))
        
        # Полная себестоимость со всеми накладными трейдинга
        total_costs = (buy_usd + fr + float(row.get('Экспортная пошлина ($)', 0.0)) + 
                       float(row.get('Прочие расходы ($)', 0.0)) + float(row.get('Сюрвей и анализы ($)', 0.0)) + 
                       float(row.get('Банковская комиссия L/C ($)', 0.0)) + row['Демередж ($)']) - row['Диспач ($)']
                       
        row['Чистая прибыль ($)'] = round(float(row.get('Цена продажи (USD)', 0.0)) - total_costs, 2)
        row['Прибыль/Тонна ($)'] = round(row['Чистая прибыль ($)'] / max(1.0, cargo), 2)
        updated_rows.append(row)
        
    st.session_state.df_data = pd.DataFrame(updated_rows)
    st.dataframe(st.session_state.df_data, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state.df_data.to_excel(writer, index=False, sheet_name='Grain_PnL_Report')
    st.download_button(label="📥 СКАЧАТЬ ФИНАНСОВЫЙ РЕЕСТР В EXCEL (.xlsx)", data=buffer.getvalue(), file_name="Grain_Finance_Report.xlsx", use_container_width=True)

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Аналитический Радар: Мониторинг Простоев и Окупаемости")
    current_today = datetime.date.today()
    
    if st.session_state.df_data.empty:
        st.info("Нет активных торговых контрактов.")
        return

    selected_deal = st.selectbox("Выберите сделку для детального финансового разбора:", list(st.session_state.df_data['ID Сделки'].unique()))
    v_rows = st.session_state.df_data[st.session_state.df_data['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        v_info = v_rows[0]
        
        st.markdown(f"### 📋 Финансово-логистический аудит судна: `{v_info.get('Название судна', 'Alpha')}`")
        st.write(f"🌍 Маршрут: **{v_info.get('Порт загрузки')}** → **{v_info.get('Порт разгрузки')}** | Инкотермс: **{v_info.get('Инкотермс')}**")
        
        st.markdown("#### 🌾 1. Результаты анализа качества и рефакции веса:")
        col_q1, col_q2, col_q3 = st.columns(3)
        col_q1.metric("Фактическая Влажность / Сор", f"{v_info.get('Влажность (%)', 14.0)}% / {v_info.get('Сорная примесь (%)', 2.0)}%")
        col_q2.metric("Скидка веса (Рефакция)", f"- {v_info.get('Рефакция веса (Тонн)', 0.0)} т.")
        col_q3.metric("Чистый оплачиваемый вес (Нетто)", f"{v_info.get('Объем выгрузки (Тонн)', 0.0)} т.")

        st.markdown("#### ⚖️ 2. Сталийное время контракта (Laytime Audit):")
        col_l1, col_l2, col_l3 = st.columns(3)
