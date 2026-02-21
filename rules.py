BAD_WORDS = [
    ,"کص", "کیر", "fuck", "sex", "تبلیغ", "پولدارشو", "جاوید شاه", "شاهزاده", "منافق", "منافقین", "سه فاسد", "جانم فدای رهبری", "شرط بندی"
]

TEAM_WORDS = [
    "همکاری", "ادمین", "مدیریت", "تیم", "ارتباط", "تماس", "همکار"
]

NEWS_WORDS = [
    "خبر", "گزارش", "اطلاعات", "بازداشت", "زندان", "دستگیری", "جاوید‌ نام", "شهید", "کشته", "اعدام", "فوری", "ویدیو", "فیلم", "عکس", "سند"
]


def classify(text: str) -> str:
    if not text:
        return "general"

    t = text.lower()

    if "http://" in t or "https://" in t or "t.me/" in t:
        return "links"

    if any(w in t for w in TEAM_WORDS):
        return "team"

    if any(w in t for w in NEWS_WORDS):
        return "news"

    if any(w in t for w in BAD_WORDS):
        return "spam"

    if len(t) > 300:
        return "long"

    return "general"
