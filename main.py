import telebot
from telebot import types
import requests
import time
import math


TOKEN = '7983424205:AAFVmLRKURpjNOs6jpgN1r7KGTTDAMdE0GU'
bot = telebot.TeleBot(TOKEN)


REQUEST_LIMIT = 10
TIME_WINDOW = 24 * 60 * 60


user_requests = {}


selected_category = {}


categories = {
    "Кафе": "cafe",
    "Ресторани": "restaurant",
    "Аптеки": "pharmacy",
    "Супермаркети": "supermarket",
    "СТО": "car_repair",
    "Побут. техніка": "electronics",
    "Красиві види": "viewpoint",
    "Розваги": "entertainment"
}


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for name in categories.keys():
        markup.add(types.KeyboardButton(name))
        bot.send_message(chat_id, "оберіть категорію", reply_markup=markup)


def can_send_request(chat_id):
    current_time = time.time()
    requestes = user_requests.get(chat_id, [])

    requestes = [req for req in requestes if current_time - req < TIME_WINDOW]
    if len(requests) >= REQUEST_LIMIT:
        return False
    requests.append(current_time)
    user_requests[chat_id] = requests
    return True

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text
    if text in categories:
        selected_category[chat_id] = categories[text]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        location_button = types.KeyboardButton(text="Надіслати геолокацію", request_location=True)
        markup.add(location_button)
        bot.send_message(chat_id, f"Ви обрали категорію: {text}. Тепер надішліть свою геолокацію.",
                         reply_markup=markup)
    else:
        bot.send_message(chat_id, "Будь ласка, оберіть категорію з клавіатури.")

@bot.message_handler(content_types=['location'])
def handle_location(message):
    chat_id = message.chat.id
    if not can_send_request(chat_id):
        bot.send_message(chat_id, "Ви досягли ліміту запитів. Спробуйте пізніше.")
        return
    if chat_id not in selected_category:
        bot.send_message(chat_id, "Будь ласка, спочатку оберіть категорію.")
        return
    latitude = message.location.latitude
    longitude = message.location.longitude
    category = selected_category[chat_id]
    bot.send_message(chat_id, "🔍 Шукаю місця поблизу...")
    places = get_places(latitude, longitude, category)
    if not places:
        bot.send_message(chat_id, "Нажаль, місць подібних до вашого запиту не було знайдено.")
        return
    markup = types.InlineKeyboardMarkup()
    for place in places:
        name = place['name']
        lat = place['lat']
        lon = place['lon']
        distance = int(place['distance'])
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
        button = types.InlineKeyboardButton(text=f"{name} ({distance} м)", url=maps_url)
        markup.add(button)
    bot.send_message(chat_id, "Місця поруч (за відстанню):", reply_markup=markup)

def get_places(lat, lon, category):
    overpass_url = "https://overpass-api.de/api/interpreter"
    if category in ["cafe", "restaurant", "pharmacy", "car_repair"]:
        query = f"""
        [out:json];
        node[amenity={category}](around:1000,{lat},{lon});
        out;
        """
    elif category in ["supermarket", "electronics"]:
        query = f"""
        [out:json];
        node[shop={category}](around:1000,{lat},{lon});
        out;
        """
    elif category == "viewpoint":
        query = f"""
        [out:json];
        node[tourism=viewpoint](around:1000,{lat},{lon});
        out;
        """
    elif category == "entertainment":
        query = f"""
        [out:json];
        node[leisure=park](around:1000,{lat},{lon});
        out;
        """
    else:
        return []
    response = requests.get(overpass_url, params={'data': query})
    data = response.json()
    places = []
    for element in data['elements']:
        name = element['tags'].get('name', 'Без назви')
        el_lat = element['lat']
        el_lon = element['lon']
        distance = calculate_distance(lat, lon, el_lat, el_lon)
        places.append({'name': name, 'lat': el_lat, 'lon': el_lon, 'distance': distance})
    # Сортуємо за відстанню
    places.sort(key=lambda x: x['distance'])
    return places[:10]

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Радіус Землі в метрах
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

bot.polling()