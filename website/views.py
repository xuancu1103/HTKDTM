import time
import PIL
from flask import Blueprint, app, render_template, flash, redirect, request, jsonify, session
import requests
from .models import Product, Cart, Order
from flask_login import login_required, current_user
from . import db
from intasend import APIService
import hashlib
import json  
import os  
import random  
from payos import PayOS ,PaymentData, ItemData  
views = Blueprint('views', __name__)
from datetime import datetime
from sqlalchemy import desc
from google.cloud import aiplatform 

import google.generativeai as genai
CLIENT_ID = "4be6c932-368c-4bf8-905e-1c65b3846151"
API_KEY = "44dea6ad-103b-45b9-904d-edc53fbca2dd"
CHECKSUM_KEY = "a02c27e9de6f352efa2a6ff0a5a3e94aa19b5efc75a5db8c423dccc6d9d19511"

payOS = PayOS(client_id=CLIENT_ID, api_key=API_KEY, checksum_key=CHECKSUM_KEY)  


# @views.route('/create_payment_link', methods=['POST'])  
# def create_payment():  
#     domain = "http://127.0.0.1:5000"  
#     try:  
#         paymentData = PaymentData(orderCode=random.randint(1000, 99999),  amount=10000, description="demo", cancelUrl=f"{domain}/orders.html", returnUrl=f"{domain}/home.html")  
#         return jsonify(payOS.createPaymentLink(paymentData))  
#     except Exception as e:  
#         return jsonify(error=str(e)), 403  




# Hàm tạo yêu cầu thanh toán đến PayOS

# def initiate_payment(amount, customer_email, customer_phone, order_id):
#     url = "https://api-merchant.payos.vn/v2/payment-requests"  # URL mới của PayOS
    
#     data = {
#         "client_id": CLIENT_ID,
#         "api_key": API_KEY,
#         "checksum_key": CHECKSUM_KEY,
#         "order_code": order_id,
#         "amount": amount,
#         "description": f"Thanh toán cho đơn hàng {order_id}",
#         "email": customer_email,
#         "phone": customer_phone
#     }
    
#     try:
#         # Gửi yêu cầu POST đến API của PayOS
#         response = requests.post(url, json=data)
#         response_data = response.json()

#         if response.status_code == 200:
#             # Kiểm tra mã lỗi và thông tin phản hồi
#             code = response_data.get("code")
#             desc = response_data.get("desc")
            
#             if code == "00":  # Mã lỗi 00 thường biểu thị thành công
#                 # Trả về link thanh toán nếu có
#                 checkout_url = response_data.get("checkoutUrl")
#                 if checkout_url:
#                     return checkout_url
#                 else:
#                     print(f"Error: {desc}")
#                     return None
#             else:
#                 print(f"Error: {desc}")
#                 return None
#         else:
#             print(f"Request failed: {response_data.get('desc', 'Unknown error')}")
#             return None
#     except Exception as e:
#         print(f"Request failed: {str(e)}")
#         return None



# Hàm gọi API thời tiết và kiểm tra xem có mưa không
def check_weather():
    # Thay YOUR_API_KEY bằng API Key của bạn từ OpenWeatherMap hoặc dịch vụ tương tự
    api_key = '07d124b17698bb1a977f8e6bdb86b4bf'
    lat = '-1.886056'
    lon = '120.524916'
    city = 'Ha Noi'  # Thành phố cần kiểm tra thời tiết
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&lang=vi&appid={api_key}&units=metric'
    # url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric'
    now = datetime.now()
    time = now.strftime("%H:%M:%S")  # Lấy thời gian theo định dạng HH:MM:SS
    date = now.strftime("%d/%m/%Y")  # Lấy ngày theo định dạng dd/mm/yyyy
    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200 and 'weather' in data:
            # Trích xuất thông tin thời tiết
            weather_info = {
                'condition': data['weather'][0]['main'],  # Điều kiện thời tiết (Rain, Clear, etc.)
                'description': data['weather'][0]['description'],  # Mô tả chi tiết
                'icon': data['weather'][0]['icon'],  # Icon thời tiết
                'temperature': round(data['main']['temp'], 1),  # Nhiệt độ
                'humidity': data['main']['humidity'],  # Độ ẩm
                'wind_speed': data['wind']['speed'],  # Tốc độ gió
                'city': data['name'],  # Thành phố
                'country': data['sys']['country'],  # Quốc gia
                'time': time,
                'date': date
            }
            return weather_info
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None


    


@views.route('/')
def home():
    
    # Lọc các sản phẩm đang giảm giá
    items = Product.query.filter_by(flash_sale=True).order_by(Product.current_price).all()
    # Nếu có mưa, thay đổi giá sản phẩm (tăng lên 20%)
     # Kiểm tra xem thời tiết có mưa không
    wearthe_infor = check_weather()
    print(wearthe_infor)
    if wearthe_infor and wearthe_infor['condition']=='Rain':
        for item in items:
            item.current_price = round(item.current_price * 1.2)  # Tăng giá lên 20%
        flash("Giá sản phẩm đã được điều chỉnh tăng do thời tiết xấu.")  # Thêm thông báo cho người dùng
    return render_template('home.html', items=items, cart=Cart.query.filter_by(customer_link=current_user.id).all()
                           if current_user.is_authenticated else [],wearther = wearthe_infor)

# Đọc dữ liệu từ file JSON
def load_fruits_data():
    with open('fruits_data.json', 'r', encoding='utf-8') as file:
        return json.load(file)

@views.route('/season')
def get_season():
    # Lấy mùa từ tham số GET
    season = request.args.get('name', None)
    if not season:
        return "Không tìm thấy mùa!", 400
    wearthe_infor = check_weather()
    fruits_data =load_fruits_data()
    if season not in fruits_data:
        return f"Mùa '{season}' không hợp lệ!", 400
    season_fruits = [fruit for fruit in fruits_data[season]]
    print(season_fruits)
    items = Product.query.filter(Product.product_name.in_(season_fruits)).order_by(Product.current_price).all()
    print(items)
    if wearthe_infor and wearthe_infor['condition']=='Rain':
        for item in items:
            item.current_price = round(item.current_price * 1.2)  # Tăng giá lên 20%
        flash("Giá sản phẩm đã được điều chỉnh tăng do thời tiết xấu.")  # Thêm thông báo cho người dùng
    
    return render_template('home.html', items=items, cart=Cart.query.filter_by(customer_link=current_user.id).all()
                           if current_user.is_authenticated else [],wearther = wearthe_infor)
    
@views.route('/add-to-cart/<int:item_id>')
@login_required
def add_to_cart(item_id):
  
    item_to_add = Product.query.get(item_id)
    item_exists = Cart.query.filter_by(product_link=item_id, customer_link=current_user.id).first()
    if item_exists:
        try:
            item_exists.quantity = item_exists.quantity + 1
            db.session.commit()
            flash(f' Quantity of { item_exists.product.product_name } has been updated')
            return redirect(request.referrer)
        except Exception as e:
            print('Quantity not Updated', e)
            flash(f'Quantity of { item_exists.product.product_name } not updated')
            return redirect(request.referrer)

    new_cart_item = Cart()
    new_cart_item.quantity = 1
    new_cart_item.product_link = item_to_add.id
    new_cart_item.customer_link = current_user.id

    try:
        db.session.add(new_cart_item)
        db.session.commit()
        flash(f'{new_cart_item.product.product_name} added to cart')
    except Exception as e:
        print('Item not added to cart', e)
        flash(f'{new_cart_item.product.product_name} has not been added to cart')

    return redirect(request.referrer)


@views.route('/cart')
@login_required
def show_cart():
    
    cart = Cart.query.filter_by(customer_link=current_user.id).all()
      # Kiểm tra xem thời tiết có mưa không
    wearthe_infor = check_weather()
    # Nếu có mưa, thay đổi giá sản phẩm (tăng lên 20%)
    if wearthe_infor and wearthe_infor['condition']=='Rain':
        for item in cart:
            item.product.current_price = round(item.product.current_price * 1.2)  # Tăng giá lên 20%  # Tăng giá lên 20%

    amount = 0
    for item in cart:
        amount += item.product.current_price * item.quantity

    return render_template('cart.html', cart=cart, amount=amount, total=amount)


@views.route('/pluscart')
@login_required
def plus_cart():
    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        cart_item = Cart.query.get(cart_id)
        cart_item.quantity = cart_item.quantity + 1
        db.session.commit()

        cart = Cart.query.filter_by(customer_link=current_user.id).all()
        # Kiểm tra xem thời tiết có mưa không
        wearthe_infor = check_weather()
        # Nếu có mưa, thay đổi giá sản phẩm (tăng lên 20%)
        if wearthe_infor and wearthe_infor['condition']=='Rain':
            for item in cart:
                item.product.current_price = round(item.product.current_price * 1.2)  # Tăng giá lên 20%  # Tăng giá lên 20%
        amount = 0

        for item in cart:
            amount += item.product.current_price * item.quantity

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'total': amount + 30000
        }

        return jsonify(data)


@views.route('/minuscart')
@login_required
def minus_cart():
    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        cart_item = Cart.query.get(cart_id)
        if cart_item.quantity >1:
            cart_item.quantity = cart_item.quantity - 1
        db.session.commit()

        cart = Cart.query.filter_by(customer_link=current_user.id).all()
           # Kiểm tra xem thời tiết có mưa không
        wearthe_infor = check_weather()
        # Nếu có mưa, thay đổi giá sản phẩm (tăng lên 20%)
        if wearthe_infor and wearthe_infor['condition']=='Rain':
            for item in cart:
                item.product.current_price = round(item.product.current_price * 1.2)  # Tăng giá lên 20%
        amount = 0

        for item in cart:
            amount += item.product.current_price * item.quantity

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'total': amount + 30000
        }

        return jsonify(data)


@views.route('removecart')
@login_required
def remove_cart():
    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        cart_item = Cart.query.get(cart_id)
        db.session.delete(cart_item)
        db.session.commit()
        
        cart = Cart.query.filter_by(customer_link=current_user.id).all()
           # Kiểm tra xem thời tiết có mưa không
        wearthe_infor = check_weather()
        # Nếu có mưa, thay đổi giá sản phẩm (tăng lên 20%)
        if wearthe_infor and wearthe_infor['condition']=='Rain':
            for item in cart:
                item.product.current_price = round(item.product.current_price * 1.2)  # Tăng giá lên 20%
        amount = 0

        for item in cart:
            amount += item.product.current_price * item.quantity

        data = {
            'quantity': cart_item.quantity,
            'amount': amount,
            'total': amount + 30000
        }

        return jsonify(data)

@views.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    cart = Cart.query.filter_by(customer_link=current_user.id).all()
      # Kiểm tra xem thời tiết có mưa không
    wearthe_infor = check_weather()
    # Nếu có mưa, thay đổi giá sản phẩm (tăng lên 20%)
    if wearthe_infor and wearthe_infor['condition']=='Rain':
        for item in cart:
            item.product.current_price = round(item.product.current_price * 1.2)  # Tăng giá lên 20%  # Tăng giá lên 20%

    amount = 0
    for item in cart:
        amount += item.product.current_price * item.quantity

    return render_template('payment.html', cart=cart, amount=amount, total=amount+30000)
@views.route('/place-order', methods=['GET', 'POST'])
@login_required
def place_order():
    customer_cart = Cart.query.filter_by(customer_link=current_user.id).all()
    address1 = "Đại học Thuỷ Lợi,Đống Đa, Hà Nội, Việt Nam"
    ship_address = request.form.get("shipping-address")
    print(ship_address)
    distance_km = calculate_distance_between_addresses(address1, ship_address)
    fee = calculate_shipping_fee(distance_km)
    print(fee)
    if customer_cart:
        try:
            print(f"Cart: {customer_cart}")  # Debugging
            total = 0
            wearthe_infor = check_weather()
            if wearthe_infor and wearthe_infor['condition']=='Rain':
                for item in customer_cart:
                    item.product.current_price = round(item.product.current_price * 1.2)  # Tăng giá lên 20%
            # Tính tổng tiền từ giỏ hàng
            for item in customer_cart:
                total += item.product.current_price * item.quantity

            # Tạo ID đơn hàng duy nhất
            order_id = f"ORDER_{current_user.id}_{int(time.time())}"
            domain = "http://127.0.0.1:5000"  

            # Tạo dữ liệu thanh toán
            payment_data = PaymentData(
                orderCode=random.randint(1000, 99999),
                amount=int(total +fee),  # Tổng tiền thanh toán
                description="Thanh toán đơn hàng",  # Mô tả đơn hàng
                cancelUrl=f"{domain}/payment-failed",  # URL khi hủy thanh toán
                returnUrl=f"{domain}/payment-success"  # URL khi thanh toán thành công
            )

            # Gọi PayOS để lấy liên kết thanh toán
            payment_url = payOS.createPaymentLink(payment_data)

            print(f"Payment URL: {payment_url}")  # Debugging

            # Kiểm tra nếu có URL thanh toán hợp lệ
            if payment_url:
                # Chuyển hướng đến URL thanh toán mà không xử lý đơn hàng ngay
                return redirect(payment_url.checkoutUrl)  # Chuyển hướng đến URL thanh toán
            else:
                flash('Payment initiation failed')
                return redirect('/')

        except Exception as e:
            print(f"Error: {e}")  # Debugging
            flash('Đặt hàng không thành công')
            return redirect('/')

    else:
        flash('Giỏ hàng của bạn đang trống')
        return redirect('/')

@views.route('/payment-success', methods=['GET', 'POST'])
def payment_success():
    try:
        # Xử lý trạng thái thanh toán, ví dụ nhận dữ liệu từ query parameters
        payment_status = request.args.get('status')
        order_code = request.args.get('orderCode')  # Lấy mã đơn hàng từ tham số URL
        print(f"Payment URL: {payment_status}")  # Debugging
        if payment_status in ['SUCCESS', 'PAID']:  # Kiểm tra nếu trạng thái là SUCCESS hoặc PAID
                # Kiểm tra trạng thái thanh toán thành công
            # Tiến hành xử lý đơn hàng
            customer_cart = Cart.query.filter_by(customer_link=current_user.id).all()
            print
            if customer_cart:
                for item in customer_cart:
                    new_order = Order()
                    new_order.quantity = item.quantity
                    new_order.price = item.product.current_price
                    new_order.status = 'Completed'  # Trạng thái đơn hàng
                    new_order.payment_id = order_code  # Gắn ID thanh toán

                    new_order.product_link = item.product_link
                    new_order.customer_link = item.customer_link

                    db.session.add(new_order)

                    # Cập nhật số lượng tồn kho sản phẩm
                    product = Product.query.get(item.product_link)
                    product.in_stock -= item.quantity

                    db.session.delete(item)  # Xóa giỏ hàng sau khi đã tạo đơn hàng
                    db.session.commit()

                flash('Đặt hàng thành công!')
                return redirect('/order-success')  # Chuyển hướng đến trang thành công
        else:
            flash('Thanh toán thất bại')
            return redirect('/payment-failed')  # Chuyển hướng đến trang thất bại

    except Exception as e:
        print(f"Error: {e}")
        flash('Có lỗi xảy ra khi xử lý đơn hàng')
        return redirect('/payment-failed')  # Chuyển hướng đến trang thất bại



@views.route('/order-success')
def order_success():
    return redirect('/')  # Trang thành công


@views.route('/payment-failed')
def payment_failed():
    return redirect('/cart')  # Trang thất bại



@views.route('/orders')
@login_required
def order():
    orders = Order.query.filter_by(customer_link=current_user.id).all()
    return render_template('orders.html', orders=orders)


@views.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search')
        items = Product.query.filter(Product.product_name.ilike(f'%{search_query}%')).all()
        return render_template('search.html', items=items, cart=Cart.query.filter_by(customer_link=current_user.id).all()
                           if current_user.is_authenticated else [])

    return render_template('search.html')




@views.route('/index')
@login_required
def index_tt():
    return render_template('index.html')  # Trang thành công





import grpc

# Cấu hình các tuỳ chọn gRPC
options = [
    ('grpc.keepalive_time', 60),  # Thời gian giữ kết nối
    ('grpc.keepalive_timeout', 20),  # Thời gian timeout
    ('grpc.max_send_message_length', 10 * 1024 * 1024),  # Kích thước tối đa của message
    ('grpc.max_receive_message_length', 10 * 1024 * 1024),  # Kích thước tối đa của message nhận
]

# Thay thế với URL server gRPC của bạn
channel = grpc.insecure_channel('localhost:5000', options=options)



# Cấu hình API Key từ biến môi trường hoặc trực tiếp
genai.configure(api_key="AIzaSyAyDCjQ1s_hXOwIRl-xN2IlVsKgyugMxck")

def find_answer_from_bank(user_question):
    with open('questions.json', 'r', encoding='utf-8') as file:
        question_bank = json.load(file)
    for item in question_bank["questions"]:
        if user_question.lower() in item["question"].lower():
            return item["answer"]
    return None
@views.route('/chat', methods=['POST'])
def chat():
    user_message = ""
    bot_reply = ""

    user_message = request.form.get("user_message")
    image_file = request.files.get("image")

    # Nếu có file ảnh được gửi lên
    if  image_file:
        print(image_file)
        image_path = os.path.join(image_file.filename)
        image_file.save(image_path)
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        organ = PIL.Image.open(image_path)
        response = model.generate_content([user_message , organ])

        if response and response.text:
            bot_reply = f"Bot đã phân tích ảnh và nhận diện được: {response.text}"
        else:
            bot_reply = "Bot không thể nhận diện được nội dung trong ảnh."
    else:
        # Nếu không có file ảnh, xử lý tin nhắn văn bản
        predefined_answer = find_answer_from_bank(user_message)
        print(predefined_answer)
        if predefined_answer:
            bot_reply = predefined_answer
        else:
            model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
            chat_session = model.start_chat(history=[])
            response = chat_session.send_message(user_message)
            bot_reply = response.text.strip() if response else "Không có phản hồi từ bot."

    return jsonify({"bot_reply": bot_reply or "Không có phản hồi nào từ bot."})

# Khởi tạo client Cohere

# co = cohere.Client("37TGKzrpX2I9wOCD1AZXLxRHAS0GguGcHORoOdve")  # Thay thế bằng API key của bạn

# @views.route('/chat', methods=['GET', 'POST'])
# def chat():
#     user_message = ""
#     bot_reply = ""
#     print(user_message)
#     if request.method == "POST":
#         data = request.get_json()  # Lấy dữ liệu JSON từ frontend
#         user_message = data.get("user_message", "")  # Truy xuất tin nhắn của người dùng
#         print(user_message)
#         try:
#             response = co.generate(
#             model="command-r-plus",
#             prompt=f"User: {user_message}\nBot:",
#             max_tokens=200,
#             temperature=0.7
#             )
#             print("heeloo",response)
#                 # Lấy phản hồi từ API Cohere
#             bot_reply = response.generations[0].text.strip()
#         except Exception as e:
#             bot_reply = "Xin lỗi, bot đang gặp sự cố. Vui lòng thử lại sau!"
#             print(f"Lỗi API Cohere: {e}")

#     # Trả về phản hồi dưới dạng JSON
#     return jsonify({"bot_reply": bot_reply or "Không có phản hồi nào từ bot."})

@views.route("/total",methods=['GET', 'POST'] )
def total():
    cart = Cart.query.filter_by(customer_link=current_user.id).all()
      # Kiểm tra xem thời tiết có mưa không
    wearthe_infor = check_weather()
    # Nếu có mưa, thay đổi giá sản phẩm (tăng lên 20%)
    if wearthe_infor and wearthe_infor['condition']=='Rain':
        for item in cart:
            item.product.current_price = round(item.product.current_price * 1.2)  # Tăng giá lên 20%  # Tăng giá lên 20%

    amount = 0
    for item in cart:
        amount += item.product.current_price * item.quantity
    address1 = "Đại học Thuỷ Lợi,Đống Đa, Hà Nội, Việt Nam"
    ship_address = request.form.get("shipping-address")
    print(ship_address)
    distance_km = calculate_distance_between_addresses(address1, ship_address)
    fee = calculate_shipping_fee(distance_km)
    print(f"Quãng đường từ {address1} đến {ship_address} là {distance_km} km và phí vận chuyển là {fee} VNĐ.")
    return render_template('payment.html', cart=cart, amount=amount, total=amount+fee, ship_address = ship_address,fee=fee,distance_km=distance_km)


def get_coordinates_from_address(address):
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&addressdetails=1"
    
    headers = {
        "User-Agent": "YourAppName/1.0 (soongxanhbgvn@gmail.com)",
        "Referer": "http://localhost:5000"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon
            else:
                raise Exception("Không tìm thấy địa chỉ.")
        else:
            raise Exception(f"Lỗi kết nối tới API, mã lỗi: {response.status_code}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Lỗi kết nối tới API: {e}")


# Hàm tính quãng đường giữa hai địa chỉ chi tiết
def calculate_distance_between_addresses(address1, address2):
    lat1, lon1 = get_coordinates_from_address(address1)
    lat2, lon2 = get_coordinates_from_address(address2)
    
    # Tiến hành tính quãng đường giữa hai điểm (sử dụng API OSRM hoặc công thức tính khoảng cách)
    return calculate_distance(lat1, lon1, lat2, lon2)

# Hàm tính quãng đường (ví dụ: sử dụng API OSRM hoặc tính theo công thức Haversine)
def calculate_distance(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        distance = data['routes'][0]['distance']  # Quãng đường tính bằng mét
        return round(distance / 1000, 2)  # Đổi sang km và làm tròn
    else:
        raise Exception("Không thể tính quãng đường.")

# Hàm tính phí vận chuyển
def calculate_shipping_fee(distance_km):
    base_fee = 10000  # Phí cơ bản (VNĐ)
    fee_per_km = 5000  # Phí mỗi km (VNĐ)
    return int(base_fee + (distance_km * fee_per_km))

# Ví dụ sử dụng
address1 = "Đại học Thuỷ Lợi,Đống Đa, Hà Nội, Việt Nam"
address2 = "Ngọc Khánh,Ba Đình ,Hà Nội"
distance_km = calculate_distance_between_addresses(address1, address2)
fee = calculate_shipping_fee(distance_km)
print(f"Quãng đường từ {address1} đến {address2} là {distance_km} km và phí vận chuyển là {fee} VNĐ.")

