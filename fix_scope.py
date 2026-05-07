d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# TW analyze block - fix scope issue
# The problem: do_single is not in session_state, so after Analyze button press
# the form inside `if do_single:` disappears on rerender before form_submit_button can fire

old_tw = "    if do_single:\n\n        with st.spinner(f\"Analyzing {single_code}...\"):\n            r = analyze(single_code, \"TW\")\n\n        if r:\n\n            st.session_state['single_result'] = r"

new_tw = "    if do_single or st.session_state.get('tw_analyzed', False):\n\n        if do_single:\n            with st.spinner(f\"Analyzing {single_code}...\"):\n                r = analyze(single_code, \"TW\")\n            st.session_state['tw_analyzed'] = True\n        elif 'single_result' in st.session_state:\n            r = st.session_state['single_result']\n        else:\n            r = None\n\n        if r:\n\n            st.session_state['single_result'] = r"

if old_tw in d:
    d = d.replace(old_tw, new_tw, 1)
    print("TW fixed!")
else:
    print("TW pattern not found")

# US analyze block
old_us = "    if do_us_single:\n\n        with st.spinner(\"Analyzing \" + us_single_code + \"...\"):\n            r = analyze(us_single_code, \"US\")\n\n        if r:\n\n            st.session_state['us_single_result'] = r"

new_us = "    if do_us_single or st.session_state.get('us_analyzed', False):\n\n        if do_us_single:\n            with st.spinner(\"Analyzing \" + us_single_code + \"...\"):\n                r = analyze(us_single_code, \"US\")\n            st.session_state['us_analyzed'] = True\n        elif 'us_single_result' in st.session_state:\n            r = st.session_state['us_single_result']\n        else:\n            r = None\n\n        if r:\n\n            st.session_state['us_single_result'] = r"

if old_us in d:
    d = d.replace(old_us, new_us, 1)
    print("US fixed!")
else:
    print("US pattern not found")

open('streamlit_tw_stock.py', 'w', encoding='utf-8').write(d)
print("Done")