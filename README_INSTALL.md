# Tharwa (ثروة) - install on another PC

## Easiest: download on any PC

Open **PowerShell** on the other PC and paste:

    irm https://raw.githubusercontent.com/Amjad2002-tech/gold-hunt/main/get.ps1 | iex

It downloads the latest Tharwa, installs Python if missing, and creates an empty profile. Each user enters their own holdings.

## الأسهل: التحميل على أي جهاز

افتح **PowerShell** على الجهاز الآخر والصق:

    irm https://raw.githubusercontent.com/Amjad2002-tech/gold-hunt/main/get.ps1 | iex

يحمّل أحدث نسخة من ثروة ويثبّتها، وكل مستخدم يدخل استثماراته الخاصة.


1. Copy `Tharwa-Setup.zip` to the other PC and unzip it (right-click > Extract All).
2. Install Python 3.11+ (Microsoft Store) if it is not there yet.
3. Double-click **Install Tharwa.bat** (or run `powershell -ExecutionPolicy Bypass -File install.ps1`).
   It installs the libraries it needs and adds Tharwa to the Start menu and Desktop.
4. Open **Tharwa** and enter **your own** gold grams and stocks, then press Save.

**Your data stays on your PC.** Each Windows user gets their own private folder
`%USERPROFILE%\Gold Hunt Data` (settings, alerts, dashboard). The zip contains no one else's holdings.
Updating or reinstalling never overwrites it; uninstalling keeps it (delete the folder to erase it).

**Optional extras** - not needed to use the app:
- WhatsApp alerts need your own WhatsApp / Meta account and keys.
- Cloud (GitHub) alerts need your own GitHub account, the GitHub CLI (`gh`), and a line
  `repo = your-name/your-repo` under `[github]` in your settings.ini. Without it, saves stay on this PC only.

The analysis in the app is historical/technical statistics, not financial advice.

---

# جولد هنت - التثبيت على جهاز آخر

1. انسخ الملف `Tharwa-Setup.zip` إلى الجهاز الآخر وفك الضغط (زر يمين > Extract All).
2. ثبّت Python 3.11 أو أحدث (من Microsoft Store) إذا لم يكن مثبتاً.
3. اضغط مرتين على **Install Tharwa.bat**. سيثبت المكتبات اللازمة ويضيف التطبيق لقائمة ابدأ وسطح المكتب.
4. افتح **ثروة** وأدخل **بياناتك أنت**: جرامات الذهب والأسهم، ثم اضغط حفظ.

**بياناتك تبقى على جهازك فقط.** لكل مستخدم مجلد خاص `%USERPROFILE%\Gold Hunt Data` فيه الإعدادات والتنبيهات.
الملف المضغوط لا يحتوي على بيانات أي شخص آخر، والتحديث أو إعادة التثبيت لا يمسح بياناتك.

**إضافات اختيارية:**
- تنبيهات واتساب تحتاج حساب واتساب / Meta خاص بك ومفاتيحك.
- تنبيهات GitHub السحابية تحتاج حساب GitHub خاص بك وأداة `gh` وسطر `repo = اسمك/المستودع` تحت `[github]` في settings.ini. بدونه يُحفظ كل شيء على هذا الجهاز فقط.

التحليل في التطبيق إحصاءات تاريخية وفنية، وليس نصيحة مالية.
