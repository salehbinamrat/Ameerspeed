# شبكة الأمير — Ameerspeed

بوابة MikroTik HotSpot بواجهة عربية متجاوبة. هذه نسخة المصدر المعدلة انطلاقا من أرشيف المستخدم بتاريخ 21 نوفمبر 2026، وليست تطبيق Windows.

## التثبيت

1. خذ نسخة احتياطية كاملة من ملفات `hotspot` الحالية على الراوتر.
2. ارفع **محتويات هذا المجلد** مباشرة إلى مجلد ملفات HotSpot على RouterOS v6، بحيث يكون `index.html` و`login.html` و`css/` و`js/` و`font/` و`img/` في المسارات نفسها.
3. استخدم HTTPS عند توفره. تحقق من أن ملفات CSS وJavaScript والـWebP والخطوط يتم تقديمها بالمسارات الصحيحة.
4. افحص الدخول الفعلي على كرت HotSpot وكرت User Manager، وحالة الدخول والخروج والكرت السابق والسرعات والكاميرا، على الهاتف الحديث والقديم قبل تعميم النسخة.

**ملاحظة:** عرض الملفات مباشرة عبر GitHub Pages لا يحاكي مصادقة MikroTik، لأن المسارات `/login` و`/status` و`/logout` يجب أن يقدمها الراوتر.

## اختبار محلي

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/browser_regression.py  # يحتاج Playwright وChromium محليين
node tests/error_mapping.test.js
python tests/browser_login_flow.py  # محاكاة ردود الراوتر
node --check js/main.min.js
```

توجد النتائج والقيود والتغييرات في [تقرير التوافق والتحسين](docs/COMPATIBILITY_REPORT_AR.md).

## تدقيق 21 نوفمبر 2026 — الأداء والمصادقة

تتضمن هذه النسخة إصلاحات POST/CHAP البديل وتأكيد انتهاء الجلسة وتقليل طلبات السرعة ورفع التوافق، مع اختبارات إضافية. ابدأ من [تقرير الإصلاح العميق](docs/DEEP_FIX_REPORT_AR.md) قبل نشرها على الراوتر. الاختبارات الآلية لا تعادل الاختبار الميداني.