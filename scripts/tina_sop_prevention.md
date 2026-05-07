# Prevent streamlit_cloud_key_conflict rule
# When defining Streamlit buttons that trigger Telegram sends:
# - Define send button OUTSIDE any "if do_single:" block
# - Use st.session_state to persist analysis results across reruns
# - The button's if-block should read r from session_state, not from a local variable
# - This is because Streamlit reruns everything from top when any widget state changes.
# - All non-widget code at the same indent level runs on every rerun, making the Send button disappear.
