def text(code: str) -> str:
    try:
        return _MESSAGES[code]
    except KeyError as exc:
        raise KeyError(code) from exc


def sheet_too_large(sheet_name: str) -> str:
    return f"شیت «{sheet_name}» از حد مجاز ردیف بیشتر است."


def too_many_columns(sheet_name: str) -> str:
    return f"شیت «{sheet_name}» از حد مجاز ستون بیشتر است."


_MESSAGES: dict[str, str] = {
    "unsupported_file_type": (
        "این نوع فایل پشتیبانی نمی‌شود. نسخه اول فقط xlsx، xls و csv را می‌پذیرد."
    ),
    "file_type_not_enabled": (
        "این نوع فایل برای نسخه‌های بعد در نظر گرفته شده و در نسخه اول فعال نیست."
    ),
    "empty_file": "فایل خالی است.",
    "empty_workbook": "هیچ داده‌ای در این فایل پیدا نشد.",
    "unreadable_workbook": "فایل خوانده نشد. ممکن است خراب یا رمزدار باشد.",
    "file_too_large": "حجم فایل از حد مجاز بیشتر است.",
    "too_many_files": "تعداد فایل‌ها در یک ارسال از حد مجاز بیشتر است.",
    "too_many_sheets": "تعداد شیت‌ها از حد مجاز بیشتر است.",
    "no_files": "هیچ فایلی ارسال نشده است.",
    "invalid_filename": "نام فایل نامعتبر است.",
    "uncompressed_too_large": "محتوای فشرده فایل از حد مجاز بزرگ‌تر است.",
    "parser_not_available": "خواندن این نوع فایل هنوز پیاده‌سازی نشده است.",
    "storage_integrity": "ذخیره فایل با محتوای دریافتی یکسان نشد.",
    "storage_conflict": "نسخه اصلی این فایل از قبل وجود دارد و بازنویسی نمی‌شود.",
    "invalid_storage_path": "مسیر ذخیره‌سازی فایل نامعتبر است.",
    "internal_error": "خطای داخلی هنگام خواندن فایل رخ داد.",
    "document_not_found": "این فایل پیدا نشد.",
}
