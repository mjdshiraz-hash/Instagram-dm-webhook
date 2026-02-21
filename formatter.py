def build_message(category, username, sender_id, text):
    if username:
        header = f"#{category} | @{username}"
    else:
        header = f"#{category} | (id:{sender_id})"

    return f"{header}\n{text}"
