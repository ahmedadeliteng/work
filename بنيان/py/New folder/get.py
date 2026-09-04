import asyncio
import random
import os
import csv
from playwright.async_api import async_playwright

async def fetch_tags_real_mouse():
    txt_file = "numbers.txt"
    output_csv = "live_results_all_tags.csv"
    
    if not os.path.exists(txt_file):
        print(f"❌ خطأ: الملف {txt_file} غير موجود!")
        return

    with open(txt_file, "r", encoding="utf-8") as f:
        numbers = [line.strip() for line in f.readlines() if line.strip()]

    print(f"إجمالي الأرقام المطلوبة: {len(numbers)} رقم.\n" + "="*40)

    if not os.path.exists(output_csv):
        with open(output_csv, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["Phone", "Main Name", "All Tags"])

    async with async_playwright() as p:
        try:
            # الاتصال بالمتصفح الرئيسي المفتوح ببورت 9222
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            print("✅ تم الاتصال بكروم بنجاح!")
        except Exception as e:
            print("❌ فشل الاتصال! تأكد من تشغيل كروم بالبورت 9222 أولاً.")
            return

        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto("https://web.getcontact.com/")
        await page.wait_for_timeout(2000)

        for index, raw_num in enumerate(numbers, 1):
            clean_num = raw_num.replace("+20", "").replace("+", "").strip()
            print(f"\n🔍 [{index}/{len(numbers)}] جاري البحث عن: {raw_num}...")
            
            try:
                if page.url != "https://web.getcontact.com/":
                    await page.goto("https://web.getcontact.com/")
                    await page.wait_for_timeout(1500)

                search_input = await page.wait_for_selector('input[placeholder*="Search"]', timeout=5000)
                
                if search_input:
                    await search_input.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    
                    await search_input.type(clean_num, delay=80)
                    
                    search_btn = await page.query_selector('button:has(svg), .search-button, button[type="submit"]')
                    if search_btn:
                        await search_btn.click()
                    else:
                        await search_input.press("Enter")

                await page.wait_for_timeout(4000)

                # فحص الكابتشا
                if "captcha" in page.url or await page.query_selector("iframe[src*='cloudflare']"):
                    print("⚠️ ظهرت كابتشا! حلها يدويًا في المتصفح ثم اضغط Enter هنا...")
                    input("اضغط Enter بعد الحل...")

                # 1. جلب الاسم الرئيسي
                main_name_el = await page.query_selector('.profile-name, h1, div[class*="name"]')
                main_name = await main_name_el.inner_text() if main_name_el else "غير مسجل"
                main_name = main_name.strip().replace("\n", " ")

                # 2. البحث عن كارت "More Tags" وضغطه بالماوس الحقيقي عبر الإحداثيات (Mouse Click)
                tag_card = page.locator('text=/More Tags/i').first
                clicked = False

                if await tag_card.is_visible():
                    await tag_card.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    
                    # جلب الإحداثيات الدقيقة للكارت في الشاشة
                    box = await tag_card.bounding_box()
                    if box:
                        # الضغط بالماوس الفيزيائي على منتصف الكارت
                        await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                        clicked = True
                        print("🖱️ تم النقر بالماوس الحقيقي على كارت التاجات!")

                if not clicked:
                    # محاولة احتياطية: النقر بالماوس على أي عنصر يحوي كلمة "tagged by"
                    alt_card = page.locator('text=/tagged by/i').first
                    if await alt_card.is_visible():
                        box = await alt_card.bounding_box()
                        if box:
                            await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                            clicked = True

                # انتظار 2.5 ثانية لتحميل وتوسيع البطاقات البيضاء
                await page.wait_for_timeout(2500)

                # 3. قراءة كل البطاقات البيضاء الظاهرة في الصورة الثانية
                tags_list = await page.evaluate('''
                    (mainName) => {
                        const tags = [];
                        const allEls = document.querySelectorAll('*');
                        
                        allEls.forEach(el => {
                            // نختار العناصر النهائية التي تحتوي على نصوص فقط (بدون أبناء)
                            if (el.children.length === 0 && el.innerText) {
                                const txt = el.innerText.trim();
                                
                                const systemWords = ['More Tags', 'This number is tagged by', 'Back', 'Call', 'Block', 'Add Tag', 'Search', 'EG +20'];
                                const isSystem = systemWords.some(w => txt.includes(w));
                                
                                if (txt && !isSystem && txt !== mainName && txt.length > 1 && txt.length < 60) {
                                    if (!tags.includes(txt)) {
                                        tags.push(txt);
                                    }
                                }
                            }
                        });
                        return tags;
                    }
                ''', main_name)

                all_tags_str = " | ".join(tags_list) if tags_list else "لا توجد تاجات إضافية"

                print(f"✅ الاسم الرئيسي: {main_name}")
                print(f"🏷️ عدد التاجات المستخرجة: {len(tags_list)}")
                print(f"📋 التاجات: {all_tags_str}")

                # حفظ النتيجة فوراً
                with open(output_csv, mode='a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow([raw_num, main_name, all_tags_str])

            except Exception as e:
                print(f"❌ خطأ مع الرقم {raw_num}: {e}")

            delay = random.uniform(3, 6)
            print(f"⏳ الانتظار {delay:.1f} ثانية...")
            await asyncio.sleep(delay)

        print("\n🎉 تم الانتهاء بنجاح! افتح ملف live_results_all_tags.csv")

if __name__ == "__main__":
    asyncio.run(fetch_tags_real_mouse())