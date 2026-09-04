import asyncio
import random
import os
import csv
from playwright.async_api import async_playwright

async def fetch_main_name_only():
    txt_file = "numbers.txt"
    output_csv = "live_results_names_only.csv"
    
    if not os.path.exists(txt_file):
        print(f"❌ خطأ: الملف {txt_file} غير موجود!")
        return

    with open(txt_file, "r", encoding="utf-8") as f:
        numbers = [line.strip() for line in f.readlines() if line.strip()]

    print(f"إجمالي الأرقام المطلوبة: {len(numbers)} رقم.\n" + "="*40 + "\n🎯 نظام السحب: الاسم الرئيسي فقط (توفير الكوتا والحساب)")

    if not os.path.exists(output_csv):
        with open(output_csv, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["Phone", "Name"])

    async with async_playwright() as p:
        try:
            # الاتصال بمتصفح كروم الرئيسي المفتوح ببورت 9222
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

                # انتظار 3.5 ثانية فقط لتحميل الاسم الرئيسي
                await page.wait_for_timeout(3500)

                # فحص الكابتشا
                if "captcha" in page.url or await page.query_selector("iframe[src*='cloudflare']"):
                    print("⚠️ ظهرت كابتشا! حلها يدويًا في المتصفح ثم اضغط Enter...")
                    input("اضغط Enter بعد الحل...")

                # جلب الاسم الرئيسي الظاهر فوق فقط
                main_name_el = await page.query_selector('.profile-name, h1, div[class*="name"]')
                main_name = await main_name_el.inner_text() if main_name_el else "غير مسجل"
                main_name = main_name.strip().replace("\n", " ")

                print(f"✅ تم الجلب: {raw_num} ---> [ {main_name} ]")

                # حفظ النتيجة فوراً في ملف live_results_names_only.csv
                with open(output_csv, mode='a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow([raw_num, main_name])

            except Exception as e:
                print(f"❌ خطأ مع الرقم {raw_num}: {e}")

            # تأخير عشوائي بين 3 إلى 5 ثوانٍ للسلامة
            delay = random.uniform(3, 5)
            print(f"⏳ الانتظار {delay:.1f} ثانية...")
            await asyncio.sleep(delay)

        print("\n🎉 تم الانتهاء بنجاح! افتح ملف live_results_names_only.csv")

if __name__ == "__main__":
    asyncio.run(fetch_main_name_only())