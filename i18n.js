// Gold Hunt - English / Arabic text for the dashboard and settings page.
// Use t('key', {v: 1}) in JS, or data-i18n="key" on an element (data-i18n-ph for placeholders).
const I18N = {
 en: {
  dir: 'ltr', switch: 'عربي',
  tab_dash: '📊 Dashboard', tab_settings: '⚙️ Settings', loading_prices: 'Loading prices…',
  // dashboard
  dash_sub: 'Updated {stamp} · 2-year analysis · Signals are historical/technical facts, not financial advice.',
  value: 'Holdings value ({c})', pl: 'Profit / loss ({c})', today: 'today', you_hold: 'You hold',
  buy_price: 'Your buy price', profit_loss: 'Profit / loss', rsi: 'RSI (14)',
  alert_above: 'Alert above', alert_below: 'Alert below', auto: '(auto)',
  range_pos: 'Range position: higher than {v}% of the last 2 years',
  lo2: '2y low {v} ({d})', hi2: '2y high {v} ({d})',
  s_price: 'Price', s_50: '50-day avg', s_200: '200-day avg', s_buy: 'Your buy', s_month: 'Avg monthly %',
  month_note: 'Right chart: average return by calendar month over 2 years — only ~2 samples per month, treat as a hint, not a rule.',
  howto: '<b>How to read:</b> <b>Range position</b> = % of the last 2 years when the price was lower. <b>RSI</b> above 70 = rose too fast, often pauses. <b>Alert levels</b> marked "auto" are unusual-move bands (50-day average ± 2 standard deviations).',
  grams: 'grams', shares: 'shares', gold_name: 'Gold 24K', unit_gram: 'SAR/gram', unit_share: '{c}/share', cur_SAR: 'SAR', cur_USD: 'USD',
  months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
  // signals (codes from gold_hunt.py)
  reason_rank: 'price is higher than {v}% of the last 2 years', reason_rsi: 'RSI {v} = overbought (rose too fast)',
  reason_stretch: '{v}% above its 200-day average (stretched)', reason_fading: 'dropped below 50-day average - uptrend may be fading',
  verdict_strong: 'Strong sell zone (historically)', verdict_watch: 'Watch closely - sell signals building', verdict_none: 'No sell signal - trend not stretched',
  trend_up: 'Uptrend', trend_down: 'Downtrend', trend_side: 'Sideways',
  // settings page
  set_title: 'Settings', set_sub: 'Change your numbers, then click <b>Save</b>. It updates this PC and GitHub together. Live prices help you pick alert levels.',
  gold_card: 'Gold (24K)', gold_help: 'How much gold you hold and what you paid per gram.',
  f_grams: 'Grams I hold', f_gold_buy: 'My buy price (SAR per gram)',
  f_move_sar: 'WhatsApp me when the price moves (SAR up or down)', f_gold_above: 'Alert me when price goes ABOVE', f_gold_below: 'Alert me when price goes BELOW',
  ph_auto_hi: 'Auto (unusual high)', ph_auto_lo: 'Auto (unusual low)', ph_auto: 'Auto',
  stocks: 'Stocks', stocks_help: 'Saudi stocks end with <b>.SR</b> (Aramco = 2222.SR, Al Rajhi = 1120.SR). US stocks use their normal ticker (NVDA, AAPL).',
  new_stock: 'New stock', remove: 'Remove', f_ticker: 'Ticker', f_name: 'Name', f_currency: 'Currency',
  ph_ticker: 'e.g. 2222.SR', ph_name: 'e.g. Aramco', f_shares: 'Shares I hold', f_stock_buy: 'My buy price (per share)',
  f_above: 'Alert me ABOVE', f_below: 'Alert me BELOW', add_stock: '+ Add a stock',
  alerts: 'Alerts', alerts_help: 'You also get a WhatsApp message when any price moves a lot in one day.',
  f_daily: 'Alert if the price moves more than (% in one day)', f_lang: 'WhatsApp message language',
  auto_q: 'What is "Auto"?', auto_a: 'If you leave an alert level empty, Gold Hunt uses an "unusual move" level: the 50-day average ± 2 standard deviations. Prices rarely go past it, so an alert there means something unusual is happening.',
  save: 'Save', ready: 'Ready', loading: 'Loading…', saving: 'Saving…', unsaved: 'Unsaved changes',
  saved_both: '✓ Saved on this PC and GitHub — used from the next check',
  saved_pc: 'Saved on this PC, but GitHub was not updated: {e}', no_server: '⚠ Could not reach the Gold Hunt program. Close this window and open the app again.',
  live_loading: 'Loading live price…', live_hint: 'Type a ticker to see its live price.',
  live_bad: 'Could not find prices for "{t}". Check the ticker (Saudi stocks end with .SR).',
  now: 'Now', your_pl: 'Your profit/loss', range: '2-year range {lo} – {hi}',
  c_buy5: 'Buy +5%', c_buy10: 'Buy +10%', c_hi_band: 'Unusual high', c_hi2: '2-year high', c_now5: 'Now +5%',
  c_buy: 'Your buy price', c_buy_m5: 'Buy −5%', c_lo_band: 'Unusual low', c_now_m5: 'Now −5%', c_auto: 'Auto',
  confirm_remove: 'Remove {n}?',
  t_live: '🟢 Live price · {t}', t_closed: '⚪ Market closed · last trade {t}', t_pulled: 'pulled {t}', t_riyadh: 'Riyadh time',
  f_ticker_search: 'Company or ticker', ph_search: 'Type a name, e.g. Al Rajhi, Apple',
  search_none: 'No match. Try the English company name or the ticker number (e.g. 1120).', search_wait: 'Searching…',
  m_saudi: 'Saudi', m_us: 'US',
 },
 ar: {
  dir: 'rtl', switch: 'English',
  tab_dash: '📊 لوحة الأسعار', tab_settings: '⚙️ الإعدادات', loading_prices: 'جاري تحميل الأسعار…',
  dash_sub: 'آخر تحديث {stamp} · تحليل آخر سنتين · الإشارات حقائق تاريخية/فنية وليست نصيحة مالية.',
  value: 'قيمة ممتلكاتك ({c})', pl: 'الربح / الخسارة ({c})', today: 'اليوم', you_hold: 'تملك',
  buy_price: 'سعر شرائك', profit_loss: 'الربح / الخسارة', rsi: 'مؤشر RSI (14)',
  alert_above: 'تنبيه أعلى من', alert_below: 'تنبيه أقل من', auto: '(تلقائي)',
  range_pos: 'موقع السعر: أعلى من {v}% من أيام آخر سنتين',
  lo2: 'أدنى سعر بالسنتين {v} ({d})', hi2: 'أعلى سعر بالسنتين {v} ({d})',
  s_price: 'السعر', s_50: 'متوسط 50 يوم', s_200: 'متوسط 200 يوم', s_buy: 'سعر شرائك', s_month: 'متوسط التغير الشهري %',
  month_note: 'الرسم الأيسر: متوسط التغير لكل شهر خلال سنتين — عينتان تقريباً لكل شهر، فاعتبره تلميحاً وليس قاعدة.',
  howto: '<b>كيف تقرأ اللوحة:</b> <b>موقع السعر</b> = نسبة الأيام في آخر سنتين التي كان السعر فيها أقل. <b>RSI</b> فوق 70 = ارتفع بسرعة وغالباً يتوقف. <b>مستويات التنبيه</b> "التلقائية" هي حدود الحركة غير العادية (متوسط 50 يوم ± انحرافين معياريين).',
  grams: 'جرام', shares: 'سهم', gold_name: 'ذهب عيار 24', unit_gram: 'ريال/جرام', unit_share: '{c}/سهم', cur_SAR: 'ريال', cur_USD: 'دولار',
  months: ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'],
  reason_rank: 'السعر أعلى من {v}% من أيام آخر سنتين', reason_rsi: 'مؤشر RSI عند {v} = تشبّع شرائي (ارتفع بسرعة)',
  reason_stretch: 'أعلى بـ {v}% من متوسط 200 يوم (مرتفع جداً)', reason_fading: 'نزل تحت متوسط 50 يوم - الاتجاه الصاعد قد يضعف',
  verdict_strong: 'منطقة بيع قوية (تاريخياً)', verdict_watch: 'راقب عن قرب - إشارات البيع تتزايد', verdict_none: 'لا توجد إشارة بيع',
  trend_up: 'اتجاه صاعد', trend_down: 'اتجاه هابط', trend_side: 'اتجاه عرضي',
  set_title: 'الإعدادات', set_sub: 'غيّر أرقامك ثم اضغط <b>حفظ</b>. يتم التحديث على هذا الجهاز وعلى GitHub معاً. الأسعار المباشرة تساعدك في اختيار مستويات التنبيه.',
  gold_card: 'الذهب (عيار 24)', gold_help: 'كمية الذهب التي تملكها وسعر شرائك للجرام.',
  f_grams: 'عدد الجرامات', f_gold_buy: 'سعر الشراء (ريال للجرام)',
  f_move_sar: 'أرسل واتساب إذا تغيّر السعر بمقدار (ريال صعوداً أو هبوطاً)', f_gold_above: 'نبهني إذا ارتفع السعر فوق', f_gold_below: 'نبهني إذا نزل السعر تحت',
  ph_auto_hi: 'تلقائي (ارتفاع غير عادي)', ph_auto_lo: 'تلقائي (انخفاض غير عادي)', ph_auto: 'تلقائي',
  stocks: 'الأسهم', stocks_help: 'الأسهم السعودية تنتهي بـ <b>.SR</b> (أرامكو = 2222.SR، الراجحي = 1120.SR). الأسهم الأمريكية برمزها العادي (NVDA، AAPL).',
  new_stock: 'سهم جديد', remove: 'حذف', f_ticker: 'الرمز', f_name: 'الاسم', f_currency: 'العملة',
  ph_ticker: 'مثال: 2222.SR', ph_name: 'مثال: أرامكو', f_shares: 'عدد الأسهم', f_stock_buy: 'سعر الشراء (للسهم)',
  f_above: 'نبهني فوق', f_below: 'نبهني تحت', add_stock: '+ إضافة سهم',
  alerts: 'التنبيهات', alerts_help: 'تصلك أيضاً رسالة واتساب إذا تحرك أي سعر كثيراً في يوم واحد.',
  f_daily: 'نبهني إذا تحرك السعر أكثر من (% في اليوم)', f_lang: 'لغة رسائل واتساب',
  auto_q: 'ماذا يعني "تلقائي"؟', auto_a: 'إذا تركت مستوى التنبيه فارغاً، يستخدم Gold Hunt مستوى "الحركة غير العادية": متوسط 50 يوم ± انحرافين معياريين. نادراً ما يتجاوزه السعر، فالتنبيه عنده يعني أن شيئاً غير عادي يحدث.',
  save: 'حفظ', ready: 'جاهز', loading: 'جاري التحميل…', saving: 'جاري الحفظ…', unsaved: 'تغييرات غير محفوظة',
  saved_both: '✓ تم الحفظ على الجهاز وعلى GitHub — يُستخدم من الفحص القادم',
  saved_pc: 'تم الحفظ على الجهاز، لكن لم يتم تحديث GitHub: {e}', no_server: '⚠ تعذّر الاتصال ببرنامج Gold Hunt. أغلق النافذة وافتح التطبيق مرة أخرى.',
  live_loading: 'جاري تحميل السعر المباشر…', live_hint: 'اكتب رمز السهم لرؤية سعره المباشر.',
  live_bad: 'لم نجد أسعاراً للرمز "{t}". تأكد من الرمز (الأسهم السعودية تنتهي بـ .SR).',
  now: 'الآن', your_pl: 'ربحك/خسارتك', range: 'نطاق السنتين {lo} – {hi}',
  c_buy5: 'الشراء +5%', c_buy10: 'الشراء +10%', c_hi_band: 'ارتفاع غير عادي', c_hi2: 'أعلى سعر بالسنتين', c_now5: 'الآن +5%',
  c_buy: 'سعر شرائك', c_buy_m5: 'الشراء −5%', c_lo_band: 'انخفاض غير عادي', c_now_m5: 'الآن −5%', c_auto: 'تلقائي',
  confirm_remove: 'حذف {n}؟',
  t_live: '🟢 سعر مباشر · {t}', t_closed: '⚪ السوق مغلق · آخر صفقة {t}', t_pulled: 'تم السحب {t}', t_riyadh: 'بتوقيت الرياض',
  f_ticker_search: 'اسم الشركة أو الرمز', ph_search: 'اكتب الاسم بالإنجليزي، مثل Al Rajhi أو Apple',
  search_none: 'لا توجد نتائج. جرّب اسم الشركة بالإنجليزي أو رقم السهم (مثل 1120).', search_wait: 'جاري البحث…',
  m_saudi: 'سعودي', m_us: 'أمريكي',
 },
};

let LANG = 'en';
try { LANG = localStorage.getItem('gh_lang') === 'ar' ? 'ar' : 'en'; } catch {}

function t(key, vars = {}) {
  const s = I18N[LANG][key] ?? I18N.en[key] ?? key;
  return typeof s === 'string' ? s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '') : s;
}

// Fill every [data-i18n] element and set the page direction
function applyI18n(root = document) {
  document.documentElement.lang = LANG;
  document.documentElement.dir = I18N[LANG].dir;
  root.querySelectorAll('[data-i18n]').forEach(el => { el.innerHTML = t(el.dataset.i18n); });
  root.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
}

// "23 Oct 14:59" in Riyadh time (Latin digits in both languages)
function fmtTime(iso) {
  if (!iso) return '–';
  const loc = LANG === 'ar' ? 'ar-SA-u-nu-latn-ca-gregory' : 'en-GB';
  return new Date(iso).toLocaleString(loc, {timeZone: 'Asia/Riyadh', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false});
}

// When the price is from + when it was pulled; older than 20 min = market closed / delayed
function timeLine(q) {
  if (!q.price_time) return '';
  const live = Date.now() - new Date(q.price_time) < 20 * 60 * 1000;
  return `${t(live ? 't_live' : 't_closed', {t: fmtTime(q.price_time)})} · ${t('t_pulled', {t: fmtTime(q.pulled_at)})} (${t('t_riyadh')})`;
}

function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem('gh_lang', lang); } catch {}
}
