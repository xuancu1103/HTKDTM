import requests
from flask import Blueprint, render_template, flash, send_from_directory, redirect,jsonify,request
from flask_login import login_required, current_user
from .forms import ShopItemsForm, OrderForm
from werkzeug.utils import secure_filename
from .models import Product, Order, Customer
from . import db
