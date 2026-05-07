d = open('streamlit_tw_stock.py', encoding='utf-8').read()

tw_has_form = 'with st.form(key="tw_single_tg_form"' in d
us_has_form = 'with st.form(key="us_single_tg_form"' in d

print(f'TW form: {tw_has_form}')
print(f'US form: {us_has_form}')
print(f'Form count: {d.count("st.form")}')
print(f'Submit button count: {d.count("form_submit_button")}')

# Verify TW button is gone
tw_has_button = 'if col1.button("Send Telegram", use_container_width=True):' in d
print(f'Old button pattern still present: {tw_has_button}')