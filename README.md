# ربات رایگان سیگنال XAUUSD — Ichimoku + Stochastic + MACD

این نسخه فقط **هشدار** می‌فرستد و هیچ معامله‌ای انجام نمی‌دهد.

## منطق سیگنال

تایم‌فریم: M15
نماد داده: `XAUUSD=X`

### BUY
- کراس صعودی Tenkan/Kijun در کندل بسته‌شده اخیر
- قیمت بالای Cloud
- Cloud صعودی
- Stochastic K بالاتر از D و K < 80
- MACD بالاتر از Signal و Histogram مثبت

### SELL
شرایط معکوس BUY.

پارامترهای پیش‌فرض:
- Ichimoku: 9 / 26 / 52
- Stochastic: 14 / 3 / 3
- MACD: 12 / 26 / 9

## راه‌اندازی با گوشی

1. در Telegram با `@BotFather` یک bot بساز و Token بگیر.
2. به ربات خودت `/start` بفرست.
3. برای گرفتن Chat ID می‌توانی در مرورگر این آدرس را باز کنی:
   `https://api.telegram.org/botTOKEN/getUpdates`
   و مقدار `chat.id` را برداری.
4. یک repository عمومی در GitHub بساز.
5. فایل‌های این پروژه را در repository قرار بده.
6. در Settings → Secrets and variables → Actions دو Secret بساز:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
7. از Actions اجرای `Gold Ichimoku Telegram Signal` را دستی اجرا کن تا تست شود.

## نکته مهم

GitHub Actions برای اجرای زمان‌بندی‌شده حداقل فاصله 5 دقیقه دارد، اما زمان‌بندی ممکن است با تأخیر اجرا شود. بنابراین این سیستم برای هشدارهای تقریبی M15 مناسب است، نه اجرای میلی‌ثانیه‌ای.

داده XAUUSD از Yahoo Finance با نماد `XAUUSD=X` گرفته می‌شود و ممکن است با قیمت/اسپرد بروکر شما دقیقاً یکسان نباشد.

وین‌ریت 85٪ تضمین نشده است. قبل از استفاده واقعی باید روی داده تاریخی و سپس حساب آزمایشی بررسی و بهینه‌سازی شود.
