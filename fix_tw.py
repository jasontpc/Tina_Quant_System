d = open('streamlit_tw_stock.py', encoding='utf-8').read()

# Fix TW single stock: replace old button pattern with form
old_tw = (
    '            st.write("DEBUG: TW Send button rendering now")\n'
    '            col1, _ = st.columns([1, 4])\n'
    '            if col1.button("Send Telegram", use_container_width=True):\n'
    '                st.info("TW send clicked")\n'
    '                st.info(f"DEBUG chat_id={TELEGRAM_CHAT_ID} token_len={len(TELEGRAM_BOT_TOKEN)}")\n'
    '                try:\n'
    '                    ok, err = push_telegram(msg)\n'
    '                    st.info(f"ok={ok} err={err}")\n'
    '                except Exception as ex:\n'
    '                    st.error(f"ex={ex}")\n'
    '                else:\n'
    '                    if ok:\n'
    '                        st.success("Telegram sent!")\n'
    '                    else:\n'
    '                        st.error(f"Failed: {err}")'
)

new_tw = (
    '            with st.form(key="tw_single_tg_form", clear_on_submit=False):\n'
    '                st.write("DEBUG: TW Send form rendering")\n'
    '                col1, _ = st.columns([1, 4])\n'
    '                submitted = st.form_submit_button("Send Telegram", use_container_width=True)\n'
    '                st.write(f"DEBUG: submitted={submitted}")\n'
    '                if submitted:\n'
    '                    st.info("TW form submitted!")\n'
    '                    st.info(f"DEBUG chat_id={TELEGRAM_CHAT_ID} token_len={len(TELEGRAM_BOT_TOKEN)}")\n'
    '                    try:\n'
    '                        ok, err = push_telegram(msg)\n'
    '                        st.info(f"ok={ok} err={err}")\n'
    '                    except Exception as ex:\n'
    '                        st.error(f"ex={ex}")\n'
    '                    else:\n'
    '                        if ok:\n'
    '                            st.success("Telegram sent!")\n'
    '                        else:\n'
    '                            st.error(f"Failed: {err}")'
)

if old_tw in d:
    d = d.replace(old_tw, new_tw, 1)
    print("TW form fixed!")
else:
    print("TW old pattern not found")
    # Check what's actually there
    idx = d.find('DEBUG: TW Send button rendering now')
    if idx >= 0:
        print(f"TW DEBUG found at {idx}")
        print(repr(d[idx:idx+500]))

open('streamlit_tw_stock.py', 'w', encoding='utf-8').write(d)
print("Done")