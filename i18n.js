// Tharwa - English / Arabic text for the dashboard and settings page.
// Use t('key', {v: 1}) in JS, or data-i18n="key" on an element (data-i18n-ph for placeholders).
const I18N = {
 en: {
  dir: 'ltr', switch: 'عربي', app_name: 'Tharwa', tagline: 'Gold &amp; stocks tracker',
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
  auto_q: 'What is "Auto"?', auto_a: 'If you leave an alert level empty, Tharwa uses an "unusual move" level: the 50-day average ± 2 standard deviations. Prices rarely go past it, so an alert there means something unusual is happening.',
  save: 'Save', ready: 'Ready', loading: 'Loading…', saving: 'Saving…', unsaved: 'Unsaved changes',
  saved_both: '✓ Saved on this PC and GitHub — used from the next check',
  saved_pc: 'Saved on this PC, but GitHub was not updated: {e}', no_server: '⚠ Could not reach the Tharwa program. Close this window and open the app again.',
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
  // live prices + chart range
  live_on: 'Live', live_ago: 'updated {s}s ago', live_off: 'Live prices only when opened from the Tharwa app',
  live_err: 'Live update failed - showing last price', mkt_closed: 'market closed', src: 'source: {s}',
  delay_rt: 'real time', delay_min: 'delayed ~{m} min', rng_label: 'Range',
  r_1m: '1M', r_3m: '3M', r_1y: '1Y', r_2y: '2Y', r_5y: '5Y',
  // behaviour analysis
  bh_title: 'History-based analysis', bh_score: 'Score {v} / 100', bh_after: 'Historically after similar days',
  bh_h: '+{h} trading days', bh_median: 'Median move', bh_up: 'Higher in', bh_cases: 'cases (separate)',
  bh_all: 'All days (baseline)', bh_cell: 'up in {p}% of {n} cases ({i} separate)',
  bh_support: 'Support', bh_resist: 'Resistance', bh_vol: 'Volatility', bh_vol_v: '{v}% a year · typical day ±{d}%',
  bh_dd: 'From peak', bh_dd_v: '{v}% (worst {m}%)', bh_none: 'none nearby', bh_match: 'match: {m}',
  bh_years: '{y} years of data (since {d})',
  match_all: 'all 4 measures', match_no_trend: 'RSI, range, distance', match_rsi_range: 'RSI and range', match_range: 'range only',
  stance_buy_zone: 'Historically a buy zone', stance_accumulate: 'Historically leaned positive',
  stance_hold: 'Historically neutral - hold / wait', stance_take_profit: 'Historically leaned negative - profit-taking zone',
  stance_sell_zone: 'Historically a sell zone',
  conf_low: 'low confidence', conf_medium: 'medium confidence', conf_high: 'high confidence',
  bh_hist60: 'historically, in similar conditions the price was higher 60 trading days later {v}% of the time',
  bh_med60: 'median move 60 trading days after similar days: {v}%',
  bh_trend_up: 'uptrend (above 50- and 200-day averages)', bh_trend_down: 'downtrend (below 50- and 200-day averages)', bh_trend_side: 'no clear trend',
  bh_above_avg: '{v}% above its 200-day average (stretched)', bh_below_avg: '{v}% below its 200-day average',
  bh_rsi_high: 'RSI {v} = overbought', bh_rsi_low: 'RSI {v} = oversold',
  bh_range_high: 'higher than {v}% of the past year', bh_range_low: 'lower than {v}% of the past year',
  bh_mom_strong: 'strong 60-day rise ({v}%)', bh_mom_weak: 'weak last 60 days ({v}%)',
  bh_season_good: 'this month has historically averaged {v}%', bh_season_bad: 'this month has historically averaged {v}%',
  bh_near_res: 'resistance (past swing high) {v}% above', bh_near_sup: 'support (past swing low) {v}% below',
  bh_drawdown: '{v}% below its peak', bh_vol_high: 'unusually volatile now ({v}% a year)',
  bh_pos_gain: 'your gain equals {v}x a typical 60-day move', bh_pos_breakeven: 'price needs {v}% to reach your buy price',
  bh_short_history: 'only {v} days of history - not enough for analysis',
  ol_title: 'Should I buy?', ol_open: 'Odds, forecast range and news',
  ol_lean_favourable: 'Historical odds favour a rise', ol_lean_neutral: 'Historical odds are balanced', ol_lean_unfavourable: 'Historical odds lean towards a fall',
  ol_score: 'Combined score {v} / 100', ol_odds: 'Chance of being higher', ol_1w: '1 week', ol_1m: '1 month', ol_3m: '3 months',
  ol_range: 'Likely range in 1 month (80% of simulations)', ol_by: 'by {d}', ol_for: 'Points for', ol_against: 'Points against',
  ol_r_behaviour: 'behaviour score {v}', ol_r_fc_up21: '{v}% of simulations end higher in 1 month', ol_r_fc_up63: '{v}% of simulations end higher in 3 months',
  ol_r_fc_dip5: '{v}% chance of touching -5% within a month', ol_r_fc_pop5: '{v}% chance of touching +5% within a month',
  ol_r_fc_buy63: '{v}% chance of being above your buy price in 3 months', ol_r_news_positive: '{v} positive headlines recently', ol_r_news_negative: '{v} negative headlines recently',
  ol_parts: 'Mix: behaviour {b} · forecast {f} · news {n}', ol_short_history: 'Not enough price history for a forecast.',
  ol_fan: 'Last 3 months and simulated range ahead', s_p50: 'Middle (p50)', s_p90: 'High (p90)', s_p10: 'Low (p10)',
  ol_table: 'Day-by-day odds ({n} dates)', c_date: 'Date', c_days: 'Trading days', c_up: 'Chance higher', c_lo: 'Likely low', c_mid: 'Likely middle', c_hi: 'Likely high',
  c_pop: 'Touch +5%', c_dip: 'Touch -5%', c_buy: 'Above buy price', ol_method: 'Method: {p} resampled paths of real past {b}-day blocks, history {y} years, trend halved.',
  ol_news: 'News', news_mood: 'Overall mood: {m} ({n} headlines)', mood_positive: 'positive', mood_negative: 'negative', mood_neutral: 'neutral',
  news_none: 'No headlines available right now.', news_err: 'News could not be loaded ({e}); showing nothing new.',
  ol_disclaimer: "Probabilities from this asset's own price history and a simple headline word count - not financial advice and not a personal recommendation. The past does not guarantee the future.",
  bh_disclaimer: 'Historical statistics only, not financial advice. The past does not guarantee the future.',
 },
 ar: {
  dir: 'rtl', switch: 'English', app_name: 'ثروة', tagline: 'متابعة الذهب والأسهم',
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
  auto_q: 'ماذا يعني "تلقائي"؟', auto_a: 'إذا تركت مستوى التنبيه فارغاً، يستخدم ثروة مستوى "الحركة غير العادية": متوسط 50 يوم ± انحرافين معياريين. نادراً ما يتجاوزه السعر، فالتنبيه عنده يعني أن شيئاً غير عادي يحدث.',
  save: 'حفظ', ready: 'جاهز', loading: 'جاري التحميل…', saving: 'جاري الحفظ…', unsaved: 'تغييرات غير محفوظة',
  saved_both: '✓ تم الحفظ على الجهاز وعلى GitHub — يُستخدم من الفحص القادم',
  saved_pc: 'تم الحفظ على الجهاز، لكن لم يتم تحديث GitHub: {e}', no_server: '⚠ تعذّر الاتصال ببرنامج ثروة. أغلق النافذة وافتح التطبيق مرة أخرى.',
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
  live_on: 'مباشر', live_ago: 'آخر تحديث قبل {s} ث', live_off: 'الأسعار المباشرة تعمل فقط عند فتح اللوحة من تطبيق ثروة',
  live_err: 'تعذّر التحديث المباشر - يظهر آخر سعر', mkt_closed: 'السوق مغلق', src: 'المصدر: {s}',
  delay_rt: 'لحظي', delay_min: 'متأخر ~{m} دقيقة', rng_label: 'المدة',
  r_1m: 'شهر', r_3m: '3 أشهر', r_1y: 'سنة', r_2y: 'سنتان', r_5y: '5 سنوات',
  bh_title: 'تحليل مبني على التاريخ', bh_score: 'النتيجة {v} / 100', bh_after: 'تاريخياً بعد أيام مشابهة',
  bh_h: '+{h} يوم تداول', bh_median: 'الحركة الوسيطة', bh_up: 'أعلى في', bh_cases: 'حالات (منفصلة)',
  bh_all: 'كل الأيام (للمقارنة)', bh_cell: 'أعلى في {p}% من {n} حالة ({i} منفصلة)',
  bh_support: 'الدعم', bh_resist: 'المقاومة', bh_vol: 'التذبذب', bh_vol_v: '{v}% سنوياً · اليوم المعتاد ±{d}%',
  bh_dd: 'من القمة', bh_dd_v: '{v}% (الأسوأ {m}%)', bh_none: 'لا يوجد قريب', bh_match: 'التطابق: {m}',
  bh_years: 'بيانات {y} سنوات (منذ {d})',
  match_all: 'المقاييس الأربعة', match_no_trend: 'RSI والنطاق والبعد عن المتوسط', match_rsi_range: 'RSI والنطاق', match_range: 'النطاق فقط',
  stance_buy_zone: 'تاريخياً منطقة شراء', stance_accumulate: 'تاريخياً يميل للإيجابية',
  stance_hold: 'تاريخياً محايد - احتفظ / انتظر', stance_take_profit: 'تاريخياً يميل للسلبية - منطقة جني أرباح',
  stance_sell_zone: 'تاريخياً منطقة بيع',
  conf_low: 'ثقة منخفضة', conf_medium: 'ثقة متوسطة', conf_high: 'ثقة عالية',
  bh_hist60: 'تاريخياً، في ظروف مشابهة كان السعر أعلى بعد 60 يوم تداول في {v}% من الحالات',
  bh_med60: 'الحركة الوسيطة بعد 60 يوم تداول من أيام مشابهة: {v}%',
  bh_trend_up: 'اتجاه صاعد (فوق متوسط 50 و200 يوم)', bh_trend_down: 'اتجاه هابط (تحت متوسط 50 و200 يوم)', bh_trend_side: 'لا يوجد اتجاه واضح',
  bh_above_avg: 'أعلى بـ {v}% من متوسط 200 يوم (مرتفع جداً)', bh_below_avg: 'أقل بـ {v}% من متوسط 200 يوم',
  bh_rsi_high: 'مؤشر RSI عند {v} = تشبّع شرائي', bh_rsi_low: 'مؤشر RSI عند {v} = تشبّع بيعي',
  bh_range_high: 'أعلى من {v}% من أيام السنة الماضية', bh_range_low: 'أقل من {v}% من أيام السنة الماضية',
  bh_mom_strong: 'صعود قوي خلال 60 يوماً ({v}%)', bh_mom_weak: 'ضعف خلال آخر 60 يوماً ({v}%)',
  bh_season_good: 'هذا الشهر كان متوسطه تاريخياً {v}%', bh_season_bad: 'هذا الشهر كان متوسطه تاريخياً {v}%',
  bh_near_res: 'مقاومة (قمة سابقة) أعلى بـ {v}%', bh_near_sup: 'دعم (قاع سابق) أقل بـ {v}%',
  bh_drawdown: 'أقل بـ {v}% من أعلى سعر له', bh_vol_high: 'تذبذب أعلى من المعتاد ({v}% سنوياً)',
  bh_pos_gain: 'ربحك يعادل {v} ضعف الحركة المعتادة خلال 60 يوماً', bh_pos_breakeven: 'يحتاج السعر {v}% ليصل إلى سعر شرائك',
  bh_short_history: 'تاريخ {v} يوم فقط - غير كافٍ للتحليل',
  ol_title: 'هل أشتري الآن؟', ol_open: 'الاحتمالات ونطاق التوقع والأخبار',
  ol_lean_favourable: 'الاحتمالات التاريخية تميل للصعود', ol_lean_neutral: 'الاحتمالات التاريخية متوازنة', ol_lean_unfavourable: 'الاحتمالات التاريخية تميل للهبوط',
  ol_score: 'النتيجة المجمّعة {v} / 100', ol_odds: 'احتمال أن يكون السعر أعلى', ol_1w: 'أسبوع', ol_1m: 'شهر', ol_3m: '3 أشهر',
  ol_range: 'النطاق المرجّح بعد شهر (80% من المحاكاة)', ol_by: 'بحلول {d}', ol_for: 'نقاط مؤيدة', ol_against: 'نقاط معارضة',
  ol_r_behaviour: 'درجة السلوك {v}', ol_r_fc_up21: '{v}% من المحاكاة تنتهي أعلى بعد شهر', ol_r_fc_up63: '{v}% من المحاكاة تنتهي أعلى بعد 3 أشهر',
  ol_r_fc_dip5: 'احتمال {v}% أن يلمس -5% خلال شهر', ol_r_fc_pop5: 'احتمال {v}% أن يلمس +5% خلال شهر',
  ol_r_fc_buy63: 'احتمال {v}% أن يكون فوق سعر شرائك بعد 3 أشهر', ol_r_news_positive: '{v} عناوين إيجابية مؤخراً', ol_r_news_negative: '{v} عناوين سلبية مؤخراً',
  ol_parts: 'المزيج: السلوك {b} · التوقع {f} · الأخبار {n}', ol_short_history: 'تاريخ الأسعار غير كافٍ للتوقع.',
  ol_fan: 'آخر 3 أشهر والنطاق المحاكى القادم', s_p50: 'الوسط (p50)', s_p90: 'الأعلى (p90)', s_p10: 'الأدنى (p10)',
  ol_table: 'الاحتمالات يوماً بيوم ({n} تاريخاً)', c_date: 'التاريخ', c_days: 'أيام التداول', c_up: 'احتمال الارتفاع', c_lo: 'الأدنى المرجّح', c_mid: 'الوسط المرجّح', c_hi: 'الأعلى المرجّح',
  c_pop: 'لمس +5%', c_dip: 'لمس -5%', c_buy: 'فوق سعر الشراء', ol_method: 'الطريقة: {p} مساراً بإعادة عيّنات من كتل حقيقية مدتها {b} أيام، تاريخ {y} سنة، مع خفض الاتجاه للنصف.',
  ol_news: 'الأخبار', news_mood: 'المزاج العام: {m} ({n} عنواناً)', mood_positive: 'إيجابي', mood_negative: 'سلبي', mood_neutral: 'محايد',
  news_none: 'لا توجد عناوين متاحة الآن.', news_err: 'تعذّر تحميل الأخبار ({e}).',
  ol_disclaimer: 'احتمالات مبنية على تاريخ سعر هذا الأصل وعدّ بسيط لكلمات العناوين - ليست نصيحة مالية ولا توصية شخصية. الماضي لا يضمن المستقبل.',
  bh_disclaimer: 'إحصاءات تاريخية فقط وليست نصيحة مالية. الماضي لا يضمن المستقبل.',
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
