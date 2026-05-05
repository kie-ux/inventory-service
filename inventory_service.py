from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)
CORS(app)

# Railway provides DATABASE_URL as an environment variable
db_url = os.environ.get('DATABASE_URL', '')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace('mysql://', 'mysql+pymysql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
    'pool_timeout': 20,
    'pool_size': 5,
    'max_overflow': 2,
}

db = SQLAlchemy(app)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id           = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), unique=True, nullable=False)
    quantity     = db.Column(db.Integer, nullable=False)

@app.before_request
def setup():
    db.create_all()
    if Inventory.query.count() == 0:
        seeds = [
            Inventory(product_name='Cobra',    quantity=50),
            Inventory(product_name='Sting',    quantity=20),
            Inventory(product_name='Red Bull', quantity=15),
            Inventory(product_name='Monster',  quantity=10),
            Inventory(product_name='Predator', quantity=16),
        ]
        db.session.add_all(seeds)
        db.session.commit()

@app.route('/update_inventory', methods=['POST'])
def update_inventory():
    try:
        root         = ET.fromstring(request.data)
        product_name = root.find('ProductName').text
        quantity     = int(root.find('Quantity').text)
        response     = ET.Element('InventoryResponse')
        item         = Inventory.query.filter_by(product_name=product_name).first()

        if item and item.quantity >= quantity:
            item.quantity -= quantity
            db.session.commit()
            ET.SubElement(response, 'Status').text       = 'Success'
            ET.SubElement(response, 'RemainingStock').text = str(item.quantity)
        else:
            ET.SubElement(response, 'Status').text  = 'Failed'
            ET.SubElement(response, 'Message').text = 'Insufficient stock or product not found'

        return Response(ET.tostring(response), mimetype='application/xml')
    except Exception as e:
        response = ET.Element('InventoryResponse')
        ET.SubElement(response, 'Status').text  = 'Error'
        ET.SubElement(response, 'Message').text = str(e)
        return Response(ET.tostring(response), mimetype='application/xml')

@app.route('/get_inventory', methods=['GET'])
def get_inventory():
    try:
        items    = Inventory.query.all()
        response = ET.Element('Inventory')
        for item in items:
            product = ET.SubElement(response, 'Product')
            ET.SubElement(product, 'Name').text  = item.product_name
            ET.SubElement(product, 'Stock').text = str(item.quantity)
        return Response(ET.tostring(response), mimetype='application/xml')
    except Exception as e:
        response = ET.Element('Inventory')
        ET.SubElement(response, 'Error').text = str(e)
        return Response(ET.tostring(response), mimetype='application/xml')

@app.route('/restock', methods=['POST'])
def restock():
    try:
        default_stock = {
            'Cobra': 50, 'Sting': 20, 'Red Bull': 15,
            'Monster': 10, 'Predator': 16,
        }
        for product_name, quantity in default_stock.items():
            item = Inventory.query.filter_by(product_name=product_name).first()
            if item:
                item.quantity = quantity
        db.session.commit()
        response = ET.Element('RestockResponse')
        ET.SubElement(response, 'Status').text  = 'Success'
        ET.SubElement(response, 'Message').text = 'All products restocked to default quantities'
        return Response(ET.tostring(response), mimetype='application/xml')
    except Exception as e:
        response = ET.Element('RestockResponse')
        ET.SubElement(response, 'Status').text  = 'Error'
        ET.SubElement(response, 'Message').text = str(e)
        return Response(ET.tostring(response), mimetype='application/xml')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)