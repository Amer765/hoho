import telebot
import requests
import json
import os
from datetime import datetime, timedelta

TOKEN = '5075951129:AAEurtYWqGhWTY5DYsnGLamRAWmRnkG3LW4'
ADMIN_ID = '2008583834'
bot = telebot.TeleBot(TOKEN)

data_file_path = 'djezzy_data.json'

def load_user_data():
    if os.path.exists(data_file_path):
        with open(data_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_user_data(data):
    with open(data_file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def hide_phone_number(phone_number):
    return phone_number[:4] + '*******' + phone_number[-2:]

def send_otp(msisdn):
    url = 'https://apim.djezzy.dz/oauth2/registration'
    payload = f'msisdn={msisdn}&client_id=6E6CwTkp8H1CyQxraPmcEJPQ7xka&scope=smsotp'
    headers = {
        'User-Agent': 'Djezzy/2.6.7',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.post(url, data=payload, headers=headers, verify=False)
        return response.status_code == 200
    except:
        return False

def verify_otp(msisdn, otp):
    url = 'https://apim.djezzy.dz/oauth2/token'
    payload = f'otp={otp}&mobileNumber={msisdn}&scope=openid&client_id=6E6CwTkp8H1CyQxraPmcEJPQ7xka&client_secret=MVpXHW_ImuMsxKIwrJpoVVMHjRsa&grant_type=mobile'
    headers = {
        'User-Agent': 'Djezzy/2.6.7',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.post(url, data=payload, headers=headers, verify=False)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_gift_payload(size):
    if size == "500":
        return {
            "id": "TransferInternet500Mo",
            "steps": 2500,
            "code": "FAMILY1000",
            "id_service": "WALKWIN"
        }
    elif size == "1":
        return {
            "id": "TransferInternet1Go",
            "steps": 5000,
            "code": "FAMILY2000",
            "id_service": "WALKWIN"
        }
    elif size == "2":
        return {
            "id": "TransferInternet2Go",
            "steps": 10000,
            "code": "FAMILY4000",
            "id_service": "WALKWIN"
        }
    return None

def apply_gift(chat_id, msisdn, access_token, username, name, size, ignore_limit=False):
    user_data = load_user_data()
    last_applied = user_data.get(str(chat_id), {}).get('last_applied')
    if last_applied and not ignore_limit:
        last_applied_time = datetime.fromisoformat(last_applied)
        if datetime.now() - last_applied_time < timedelta(days=1):
            bot.send_message(chat_id, "⚠️ لا يمكنك استخدام الهدية الآن. الرجاء الانتظار 24 ساعة.")
            return False

    gift_data = get_gift_payload(size)
    if not gift_data:
        bot.send_message(chat_id, "⚠️ حجم غير صحيح.")
        return False

    url = f'https://apim.djezzy.dz/djezzy-api/api/v1/subscribers/{msisdn}/subscription-product?include='
    payload = {
        "data": {
            "id": gift_data["id"],
            "type": "products",
            "meta": {
                "services": {
                    "steps": gift_data["steps"],
                    "code": gift_data["code"],
                    "id": gift_data["id_service"]
                }
            }
        }
    }
    headers = {
        'User-Agent': 'Djezzy/2.6.7',
        'Content-Type': 'application/json; charset=utf-8',
        'Authorization': f'Bearer {access_token}'
    }
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False)
        res_data = response.json()
        if "successfully done" in res_data.get("message", ""):
            hidden = hide_phone_number(msisdn)
            msg = f"✅ تم تفعيل باقة {size} بنجاح!\n👤 الاسم: {name}\n🧑‍💻 المستخدم: @{username}\n📞 الرقم: {hidden}"
            bot.send_message(chat_id, msg)
            user_data[str(chat_id)]['last_applied'] = datetime.now().isoformat()
            save_user_data(user_data)
            return True
        else:
            bot.send_message(chat_id, f"⚠️ خطأ: {res_data.get('message', 'غير معروف')}")
            return False
    except:
        bot.send_message(chat_id, "⚠️ حدث خطأ أثناء التفعيل.")
        return False

@bot.message_handler(commands=['start'])
def start(msg):
    chat_id = msg.chat.id
    bot.send_message(chat_id, "👋 أرسل رقم Djezzy (مثال: 077...)")
    bot.register_next_step_handler_by_chat_id(chat_id, handle_number)

def handle_number(msg):
    chat_id = msg.chat.id
    number = msg.text
    if number.startswith("07") and len(number) == 10:
        msisdn = '213' + number[1:]
        if send_otp(msisdn):
            bot.send_message(chat_id, "🔢 أدخل رمز OTP المرسل إليك:")
            bot.register_next_step_handler_by_chat_id(chat_id, lambda m: handle_otp(m, msisdn))
        else:
            bot.send_message(chat_id, "⚠️ فشل في إرسال OTP.")
    else:
        bot.send_message(chat_id, "⚠️ الرقم غير صالح.")

def handle_otp(msg, msisdn):
    chat_id = msg.chat.id
    otp = msg.text
    tokens = verify_otp(msisdn, otp)
    if tokens:
        user_data = load_user_data()
        user_data[str(chat_id)] = {
            'username': msg.from_user.username,
            'telegram_id': chat_id,
            'msisdn': msisdn,
            'access_token': tokens['access_token'],
            'refresh_token': tokens['refresh_token'],
            'last_applied': None
        }
        save_user_data(user_data)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("500Mo", callback_data="gift_500"),
            telebot.types.InlineKeyboardButton("1Go", callback_data="gift_1"),
            telebot.types.InlineKeyboardButton("2Go", callback_data="gift_2")
        )
        markup.row(
            telebot.types.InlineKeyboardButton("تفعيل كل العروض", callback_data="gift_all")
        )
        bot.send_message(chat_id, "✅ تحقق ناجح! اختر الباقة:", reply_markup=markup)
    else:
        bot.send_message(chat_id, "⚠️ رمز OTP غير صحيح.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("gift_") and call.data != "gift_all")
def gift_callback(call):
    chat_id = call.message.chat.id
    size = call.data.split("_")[1]
    user_data = load_user_data()
    if str(chat_id) in user_data:
        user = user_data[str(chat_id)]
        apply_gift(chat_id, user['msisdn'], user['access_token'], user['username'], call.from_user.first_name, size)

@bot.callback_query_handler(func=lambda call: call.data == "gift_all")
def gift_all_callback(call):
    chat_id = call.message.chat.id
    user_data = load_user_data()
    if str(chat_id) in user_data:
        user = user_data[str(chat_id)]
        sizes = ["500", "1", "2"]
        success = []
        for size in sizes:
            result = apply_gift(chat_id, user['msisdn'], user['access_token'], user['username'], call.from_user.first_name, size, ignore_limit=True)
            if result:
                success.append(size)
        if success:
            bot.send_message(chat_id, f"✅ تم تفعيل العروض التالية بالترتيب: {', '.join(success)}")
        else:
            bot.send_message(chat_id, "⚠️ لم يتم تفعيل أي عرض.")

print("✅ البوت شغال...")
bot.polling()