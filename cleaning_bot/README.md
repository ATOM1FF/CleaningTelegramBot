# Telegram buyurtma bot

Gilam, parda, adyol-ko'rpa va boshqa matolarni tozalash xizmatlari uchun aiogram 3 asosidagi Telegram bot. Buyurtmalar, mijozlar, operatorlar va tugallanmagan FSM jarayonlari SQLite’da saqlanadi.

## Loyiha tuzilmasi

```text
cleaning_bot/
  database/
    db.py              # Buyurtmalar, mijozlar, operatorlar va statistika
    storage.py         # Restartdan keyin FSM holatlarini tiklash
  handlers/
    common.py          # /start, til va mijoz menyusi
    orders.py          # FSM buyurtma jarayoni va operatorga yuborish
    operators.py       # Buyurtma holatini operator tugmalari bilan boshqarish
    admin.py           # Admin panel, statistika, Excel va ommaviy xabar
  keyboards/
    keyboards.py       # Reply va inline klaviaturalar
  locales/
    uz.py, ru.py, en.py
  utils/
    formatting.py      # Buyurtma matnlarini shakllantirish
    reports.py         # XLSX hisobot
    validation.py      # Telefon va o'lcham tekshiruvlari
  config.py
  main.py
  states.py
  requirements.txt
  .env.example
```

## O'rnatish

Python 3.11 yoki undan yangi versiya talab qilinadi.

```powershell
cd C:\Users\salom\cleaning_bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` faylida quyidagilarni o'zgartiring:

- `BOT_TOKEN`: BotFather bergan token.
- `ADMIN_IDS`: adminlarning Telegram ID raqamlari, vergul bilan ajrating.
- `CHANNEL_ID`: kanalning raqamli ID raqami. Botni kanalga administrator qilib qo'shing.
- `BUSINESS_NAME`, `CONTACT_PHONE`: korxona ma'lumotlari.
- `RATE_LIMIT_SECONDS`: mijoz qayta zayavka yuborishi orasidagi soniyalar.

Operator bot orqali shaxsiy xabar olishi uchun avval botga `/start` yuborgan bo'lishi kerak. Admin `/admin` panelidan operator ID raqamini qo'shadi. Operator tugmasini kanalga ham chiqaramiz; kanalga bot administrator huquqlari berilgan bo'lishi shart.

## Ishga tushirish

```powershell
python main.py
```

Botni to'xtatish uchun `Ctrl+C` bosing. `DATABASE_PATH` standart holatda `cleaning_bot.sqlite3`; shu faylni saqlab qolish va zaxiralash orqali ma'lumotlar saqlanadi. FSM holatlari ham shu bazada turadi.

## Asosiy imkoniyatlar

- Uch tilda (o'zbek, rus, ingliz) mijoz interfeysi va bazada saqlanadigan til tanlovi.
- Bir buyurtmaga bir nechta mato turi, o'lcham, miqdor, izoh va ixtiyoriy rasm.
- Operator/admin uchun qabul qilish, jarayonga o'tkazish, bajarish va bekor qilish tugmalari. Buyurtmani birinchi qabul qilgan operator band sifatida ko'rsatiladi.
- Admin statistikasi: haftalik (joriy hafta), oylik (joriy oy), yillik (joriy yil), XLSX eksport.
- Statistika jami/bajarilgan/bekor qilingan arizalarni barcha holatlardan sanaydi; yuvilgan dona, maydon va mato turlari taqsimotini faqat bajarilgan buyurtmalardan hisoblaydi.
- Admin panelidan holat bo'yicha so'nggi 15 ta buyurtma, operatorlar, mijozlar soni va ommaviy xabar.

Narxni bot ko'rsatmaydi; tasdiqdan keyin mijozga operator bog'lanishi haqida xabar yuboriladi. Kanal yuborishi, operatorga shaxsiy yuborish va mijozga holat xabari Telegram botga kerakli chatlarda yozish huquqi berilganida ishlaydi.

## Testlar

```powershell
python -m unittest discover -s tests -v
```
