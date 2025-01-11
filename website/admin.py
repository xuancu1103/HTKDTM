from flask import Blueprint, render_template, flash, send_from_directory, redirect
from flask_login import login_required, current_user
from .forms import ShopItemsForm, OrderForm
from werkzeug.utils import secure_filename
from .models import Product, Order, Customer
import plotly.express as px
import plotly.io as pio
from . import db
import pandas as pd

import os  
import json  



admin = Blueprint('admin', __name__)


@admin.route('/media/<path:filename>')
def get_image(filename):
    return send_from_directory('../media', filename)

# Helper function to save the JSON file
def save_json_file(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
def load_json_file(file_path):
    if not os.path.exists(file_path):
        return {"Thit": [], "Rau": [], "Qua": []}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
@admin.route('/add-shop-items', methods=['GET', 'POST'])
@login_required
def add_shop_items():
    if current_user.id == 1:
        form = ShopItemsForm()

        if form.validate_on_submit():
            product_name = form.product_name.data
            current_price = form.current_price.data
            previous_price = form.previous_price.data
            in_stock = form.in_stock.data
            flash_sale = form.flash_sale.data
            category = form.category.data
            file = form.product_picture.data

            file_name = secure_filename(file.filename)

            file_path = f'./media/{file_name}'

            file.save(file_path)

            new_shop_item = Product()
            new_shop_item.product_name = product_name
            new_shop_item.current_price = current_price
            new_shop_item.previous_price = previous_price
            new_shop_item.in_stock = in_stock
            new_shop_item.flash_sale = flash_sale

            new_shop_item.product_picture = file_path

            json_file_path = "./fruits_data.json"
            product_data = load_json_file(json_file_path)
            product_data[category].append(product_name)
            save_json_file(product_data, json_file_path)
            try:
                db.session.add(new_shop_item)
                db.session.commit()
                flash(f'{product_name} added Successfully')
                print('Product Added')
                return render_template('add_shop_items.html', form=form)
            except Exception as e:
                print(e)
                flash('Product Not Added!!')

        return render_template('add_shop_items.html', form=form)

    return render_template('404.html')


@admin.route('/shop-items', methods=['GET', 'POST'])
@login_required
def shop_items():
    if current_user.id == 1:
        items = Product.query.order_by(Product.date_added).all()
        return render_template('shop_items.html', items=items)
    return render_template('404.html')


@admin.route('/update-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def update_item(item_id):
    if current_user.id == 1:
        form = ShopItemsForm()

        item_to_update = Product.query.get(item_id)

        form = ShopItemsForm(
            product_name=item_to_update.product_name,
            previous_price=item_to_update.previous_price,
            current_price=item_to_update.current_price,
            in_stock=item_to_update.in_stock,
            flash_sale=item_to_update.flash_sale,
        )

        if form.validate_on_submit():
            product_name = form.product_name.data
            current_price = form.current_price.data
            previous_price = form.previous_price.data
            in_stock = form.in_stock.data
            flash_sale = form.flash_sale.data

            file = form.product_picture.data

            file_name = secure_filename(file.filename)
            file_path = f'./media/{file_name}'

            file.save(file_path)

            try:
                Product.query.filter_by(id=item_id).update(dict(product_name=product_name,
                                                                current_price=current_price,
                                                                previous_price=previous_price,
                                                                in_stock=in_stock,
                                                                flash_sale=flash_sale,
                                                                product_picture=file_path))

                db.session.commit()
                flash(f'{product_name} updated Successfully')
                print('Product Upadted')
                return redirect('/shop-items')
            except Exception as e:
                print('Product not Upated', e)
                flash('Item Not Updated!!!')

        return render_template('update_item.html', form=form)
    return render_template('404.html')


@admin.route('/delete-item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def delete_item(item_id):
    if current_user.id == 1:
        try:
            item_to_delete = Product.query.get(item_id)
            db.session.delete(item_to_delete)
            db.session.commit()
            flash('One Item deleted')
            return redirect('/shop-items')
        except Exception as e:
            print('Item not deleted', e)
            flash('Item not deleted!!')
        return redirect('/shop-items')

    return render_template('404.html')


@admin.route('/view-orders')
@login_required
def order_view():
    if current_user.id == 1:
        orders = Order.query.all()
        total_amount = sum(order.price * order.quantity for order in orders if order.status == 'Completed')
        return render_template('view_orders.html', orders=orders, total_amount=total_amount)
    return render_template('404.html')

@admin.route('/chart')
@login_required
def chart_view():
    if current_user.id == 1:
        status_counts = db.session.query(Order.status, db.func.count(Order.status).label('count'))\
            .group_by(Order.status).all()

        # Chuyển dữ liệu thành dạng dictionary
        data = [{'status': status, 'count': count} for status, count in status_counts]

        # Tạo biểu đồ cột với Plotly
        df = pd.DataFrame(data)
        fig = px.bar(df, x='status', y='count', title="Status Distribution", labels={'status': 'Status', 'count': 'Count'})

        # Chuyển biểu đồ thành HTML
        graph_html = pio.to_html(fig, full_html=False)

        status_stats = db.session.query(
            Order.status,
            db.func.sum(Order.price).label('total_price')
        ).group_by(Order.status).all()

        # Chuyển dữ liệu thành dạng dictionary
        data = [{'status': status, 'total_price': total_price} 
                for status, total_price in status_stats]
        print(data)
        # Tạo biểu đồ cột với Plotly (bao gồm cả tổng giá trị)
        df = pd.DataFrame(data)
        fig = px.bar(df, 
                     x='status', 
                     y='total_price', 
                     title="Total Price by Status", 
                     labels={'status': 'Status', 'total_price': 'Total Price'})

        # Chuyển biểu đồ thành HTML
        graph_html1 = pio.to_html(fig, full_html=False)
        # Trả về template với biểu đồ
        return render_template('chart_view.html', graph_html=graph_html,graph_html1 = graph_html1)

@admin.route('/update-order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def update_order(order_id):
    if current_user.id == 1:
        form = OrderForm()

        order = Order.query.get(order_id)

        if form.validate_on_submit():
            status = form.order_status.data
            order.status = status

            try:
                db.session.commit()
                flash(f'Order {order_id} Updated successfully')
                return redirect('/view-orders')
            except Exception as e:
                print(e)
                flash(f'Order {order_id} not updated')
                return redirect('/view-orders')

        return render_template('order_update.html', form=form)

    return render_template('404.html')


@admin.route('/customers')
@login_required
def display_customers():
    if current_user.id == 1:
        customers = Customer.query.all()
        
        return render_template('customers.html', customers=customers)
    return render_template('404.html')


@admin.route('/admin-page')
@login_required
def admin_page():
    if current_user.id == 1:
        return render_template('admin.html')
    return render_template('404.html')









