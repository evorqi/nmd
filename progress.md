# پیشرفت nmd

## Part 1 — Foundation و Ingestion

وضعیت: PART COMPLETE

شامل می‌شود:

- رجیستری نوع فایل با پشتیبانی فعال `xlsx` / `xls` / `csv`
- ذخیره نسخه Original تغییرناپذیر
- خلاصه ساختاری شیت‌ها
- رابط فارسی آپلود

شامل نمی‌شود:

- معنای ستون، هشدار کیفیت، پاک‌سازی، تطبیق، Chat، نمودار، داشبورد

بررسی انجام‌شده:

- pytest: ۲۷ پاس
- ruff: پاس
- mypy: پاس
- typecheck، lint و build فرانت‌اند: پاس
- اجرای API و بازنویسی Next
- مرورگر: خواندن `فروش.xlsx` و `فروش.csv`، رد شدن فایل خالی، چیدمان باریک

## باقی‌مانده

- Part 2 — Understand
- Part 3 — Clean + Preview + Version
- Part 4 — Match
- Part 5 — Workbook operations + Formula + Build
- Part 6 — Analyze + Chart + Dashboard + Export
- Part 7 — Agent
- Part 8 — Hardening
