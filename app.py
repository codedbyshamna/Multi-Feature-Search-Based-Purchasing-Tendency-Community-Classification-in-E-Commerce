from flask import Flask,render_template,request,redirect,session
import os
import mysql.connector
import numpy as np
import torch
import pandas as pd
import random
from flask_mail import Mail, Message

def get_db():

    conn=mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="purchasing_tendency",
        charset="utf8"
    )

    return conn

app=Flask(__name__)
app.secret_key=os.getenv('FLASK_SECRET_KEY')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'projectbased2k26@gmail.com'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = 'projectbased2k26@gmail.com'

mail = Mail(app)

UPLOAD_FOLDER="static/uploads/products"
app.config["UPLOAD_FOLDER"]=UPLOAD_FOLDER

df = pd.read_csv("static/data/dataset.csv")
data = pd.read_csv("static/data/ecommerce_behavior_dataset.csv")
# ------------------------------------------------
# HOME
# ------------------------------------------------

@app.route("/")
def index():

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products")
    products=cur.fetchall()

    return render_template("index.html",products=products)



# ------------------------------------------------
# ADMIN
# ------------------------------------------------

# ADMIN
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if ADMIN_PASSWORD and username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = "admin"
            return redirect("/admin_dashboard")

        return "Invalid username or password", 401

    return render_template("admin_login.html")



@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin")

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM sellers")
    sellers=cur.fetchall()

    cur.execute("SELECT * FROM buyers")
    buyers=cur.fetchall()

    return render_template("admin_dashboard.html",sellers=sellers,buyers=buyers)

@app.route("/admin_analytics")
def admin_analytics():

    if "admin" not in session:
        return redirect("/admin")

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    # Calculate interaction score for products
    cur.execute("""
    SELECT products.id,
           products.name,
           COUNT(interactions.product_id) AS score
    FROM interactions
    JOIN products ON products.id = interactions.product_id
    GROUP BY interactions.product_id
    ORDER BY score DESC
    """)

    products=cur.fetchall()

    return render_template("admin_analytics.html",products=products)

@app.route("/remove_seller/<id>")
def remove_seller(id):

    conn=get_db()
    cur=conn.cursor()

    cur.execute("DELETE FROM sellers WHERE id=%s",(id,))
    conn.commit()

    return redirect("/admin_dashboard")



# ------------------------------------------------
# SELLER REGISTER
# ------------------------------------------------

@app.route("/seller_register",methods=["GET","POST"])
def seller_register():

    if request.method=="POST":

        name=request.form["name"]
        email=request.form["email"]
        mobile=request.form["mobile"]
        shopname=request.form["shopname"]
        address=request.form["address"]
        category=request.form["category"]
        lat=request.form["latitude"]
        lon=request.form["longitude"]
        username=request.form["username"]
        password=request.form["password"]

        conn=get_db()
        cur=conn.cursor()

        sql="""INSERT INTO sellers
        (name,email,mobile,shopname,address,category,latitude,longitude,username,password)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

        cur.execute(sql,(name,email,mobile,shopname,address,category,lat,lon,username,password))
        conn.commit()

        return redirect("/seller_login")

    return render_template("seller_register.html")



# ------------------------------------------------
# SELLER LOGIN
# ------------------------------------------------

@app.route("/seller_login",methods=["GET","POST"])
def seller_login():

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        conn=get_db()
        cur=conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM sellers WHERE username=%s AND password=%s",(username,password))
        seller=cur.fetchone()

        if seller:

            session["seller"]=seller["id"]

            return redirect("/seller_dashboard")

    return render_template("seller_login.html")

@app.route("/seller_dash")
def dash():
    import pandas as pd
    import random

    df = pd.read_csv("static/data/ecommerce_dataset_fixed.csv")
    purchases = df[df["action"] == "purchase"]

    # --------------------------------
    # Total demand per location
    # --------------------------------
    location_totals = (
        purchases.groupby("location")
        .size()
        .reset_index(name="total_demand")
    )

    # --------------------------------
    # Product demand per location
    # --------------------------------
    location_products = (
        purchases.groupby(["location", "product_name"])
        .size()
        .reset_index(name="count")
    )

    # --------------------------------
    # Coordinates
    # --------------------------------
    coordinates = {
        "Chennai": (13.0827, 80.2707),
        "Delhi": (28.7041, 77.1025),
        "Mumbai": (19.0760, 72.8777),
        "Bangalore": (12.9716, 77.5946),
        "Hyderabad": (17.3850, 78.4867),
        "Pune": (18.5204, 73.8567),
        "Kolkata": (22.5726, 88.3639),
        "Madurai": (9.9252, 78.1198),
        "Coimbatore": (11.0168, 76.9558),
        "Trichy": (10.7905, 78.7047)
    }

    # --------------------------------
    # Demand thresholds
    # --------------------------------
    min_val = location_totals["total_demand"].min()
    max_val = location_totals["total_demand"].max()

    medium_threshold = min_val + (max_val - min_val) * 0.4
    high_threshold = min_val + (max_val - min_val) * 0.7

    # --------------------------------
    # Map points
    # --------------------------------
    map_data = []

    for _, row in location_products.iterrows():

        loc = row["location"]
        product = row["product_name"]
        demand = row["count"]

        if loc not in coordinates:
            continue

        total_loc_demand = int(
            location_totals[location_totals["location"] == loc]["total_demand"].values[0]
        )

        # demand level by location total
        if total_loc_demand <= medium_threshold:
            level = "low"
        elif total_loc_demand <= high_threshold:
            level = "medium"
        else:
            level = "high"

        lat, lng = coordinates[loc]

        # offset so markers don't overlap
        lat += random.uniform(-0.04, 0.04)
        lng += random.uniform(-0.04, 0.04)

        map_data.append({
            "name": loc,
            "lat": lat,
            "lng": lng,
            "product": product,
            "demand": int(demand),
            "level": level
        })

    # --------------------------------
    # Top products list for cards
    # --------------------------------
    location_data = {}

    for loc in location_products["location"].unique():

        loc_df = location_products[location_products["location"] == loc]

        top = loc_df.sort_values("count", ascending=False).head(5)

        location_data[loc] = {
            "products": top["product_name"].tolist(),
            "counts": top["count"].tolist()
        }

    return render_template(
        "dash.html",
        map_data=map_data,
        location_data=location_data
    )
@app.route("/analytics")
def analytics():

    import pandas as pd

    df = pd.read_csv("static/data/ecommerce_dataset_fixed.csv")

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d-%m-%y")

    purchases = df[df["action"] == "purchase"]

    # Top selling products
    product_popularity = (
        purchases.groupby("product_name")
        .size()
        .sort_values(ascending=False)
        .head(8)
    )

    # Demand by location
    location_demand = purchases.groupby("location").size()

    # Category demand
    category_demand = purchases.groupby("category").size()

    # Monthly sales trend
    sales_trend = purchases.groupby(purchases["timestamp"].dt.month).size()

    return render_template(
        "analytics.html",

        products=product_popularity.index.tolist(),
        product_counts=product_popularity.values.tolist(),

        locations=location_demand.index.tolist(),
        location_counts=location_demand.values.tolist(),

        categories=category_demand.index.tolist(),
        category_counts=category_demand.values.tolist(),

        months=sales_trend.index.tolist(),
        sales=sales_trend.values.tolist()
    )

# -------------------------------------------------
# DEMAND INSIGHT ALERT ENGINE
# -------------------------------------------------

def generate_demand_alerts():

    df = pd.read_csv("static/data/ecommerce_dataset_fixed.csv")

    purchases = df[df["action"] == "purchase"]

    alerts = []

    demand = (
        purchases.groupby(["location","product_name"])
        .size()
        .reset_index(name="count")
    )

    for _, row in demand.iterrows():

        location = row["location"]
        product = row["product_name"]
        count = row["count"]

        if count >= 25:

            alerts.append({
                "type": "high",
                "message": f"High demand for {product} in {location}. Increase inventory."
            })

        elif count <= 5:

            alerts.append({
                "type": "low",
                "message": f"Low demand for {product} in {location}. Consider promotions."
            })

    # --------------------------------
    # RETURN ONLY ONE RANDOM ALERT
    # --------------------------------
    if alerts:
        return random.choice(alerts)

    return None

def generate_seller_alert():

    df = pd.read_csv("static/data/ecommerce_dataset_fixed.csv")

    purchases = df[df["action"] == "purchase"]

    alerts = []

    demand = (
        purchases.groupby(["location","product_name"])
        .size()
        .reset_index(name="count")
    )

    for _, row in demand.iterrows():

        location = row["location"]
        product = row["product_name"]
        count = row["count"]

        # 🚀 High demand
        if count >= 25:
            alerts.append({
                "type":"high",
                "icon":"🚀",
                "title":"High Demand Alert",
                "message":f"{product} demand is high in {location}. Increase stock."
            })

        # 📉 Low demand
        elif count <= 5:
            alerts.append({
                "type":"low",
                "icon":"📉",
                "title":"Low Demand Warning",
                "message":f"{product} demand is low in {location}. Consider promotion."
            })

        # 🔥 Trending
        elif 15 <= count < 25:
            alerts.append({
                "type":"trend",
                "icon":"🔥",
                "title":"Trending Product",
                "message":f"{product} is trending in {location}."
            })

        # 📍 Market opportunity
        elif count < 10:
            alerts.append({
                "type":"opportunity",
                "icon":"📍",
                "title":"Location Opportunity",
                "message":f"{product} may have potential demand in {location}."
            })

    if alerts:
        return random.choice(alerts)

    return None

def send_alert_email(email, alerts):

    if not alerts:
        return

    alert_text = ""

    for alert in alerts:
        alert_text += f"- {alert['message']}\n"

    msg = Message(
        subject="Demand Insight Alert",
        recipients=[email],
        body=f"""
Hello Seller,

Our system detected important demand insights:

{alert_text}

Please adjust your inventory accordingly.

Purchasing Intelligence System
"""
    )

    mail.send(msg)
    
@app.route("/seller_dashboard")
def seller_dashboard():

    if "seller" not in session:
        return redirect("/seller_login")

    alert = generate_seller_alert()

    return render_template(
        "seller_dashboard.html",
        alert=alert
    )

@app.route("/community")
def community():

    df["interaction"] = df["views"] + df["carts"] + df["purchases"]

    grouped = df.groupby("district").agg({
        "views":"sum",
        "carts":"sum",
        "purchases":"sum"
    }).reset_index()

    districts = grouped["district"].tolist()
    views = grouped["views"].tolist()
    carts = grouped["carts"].tolist()
    purchases = grouped["purchases"].tolist()

    return render_template(
        "community_dashboard.html",
        districts=districts,
        views=views,
        carts=carts,
        purchases=purchases
    )

# -----------------------------
# SEQUENTIAL BEHAVIOR
# -----------------------------

@app.route("/sequential")
def buyer_recommendation():

    # total purchases per location and product
    data = df.groupby(["district","product"])["purchases"].sum().reset_index()

    # pick top product per district
    top = data.sort_values("purchases", ascending=False).groupby("district").head(1)

    locations = top["district"].tolist()
    products = top["product"].tolist()
    scores = top["purchases"].tolist()

    return render_template(
        "sequential_dashboard.html",
        locations=locations,
        products=products,
        scores=scores
    )
# DEMAND INSIGHT
# -----------------------------

@app.route("/demand")
def demand():

    grouped = df.groupby(["product","district"])["purchases"].sum().reset_index()

    products = {}

    for product in grouped["product"].unique():

        data = grouped[grouped["product"] == product]

        locations = data["district"].tolist()
        values = data["purchases"].tolist()

        colors = []

        for v in values:
            if v < 10:
                colors.append("#ff4d4d")   # red
            elif v < 20:
                colors.append("#ffc107")   # yellow
            else:
                colors.append("#28a745")   # green

        products[product] = {
            "locations": locations,
            "values": values,
            "colors": colors
        }

    return render_template("demand_dashboard.html", products=products)

# ------------------------------------------------
# ADD PRODUCT
# ------------------------------------------------

@app.route("/add_product",methods=["GET","POST"])
def add_product():

    if "seller" not in session:
        return redirect("/seller_login")

    if request.method=="POST":

        name=request.form["name"]
        price=request.form["price"]
        specification=request.form["specification"]

        file=request.files["image"]

        filename=file.filename
        filepath=os.path.join(app.config["UPLOAD_FOLDER"],filename)
        file.save(filepath)

        conn=get_db()
        cur=conn.cursor()

        cur.execute("""
        INSERT INTO products
        (seller_id,name,price,specification,image)
        VALUES(%s,%s,%s,%s,%s)
        """,(session["seller"],name,price,specification,filename))

        conn.commit()

        return redirect("/view_products")

    return render_template("add_product.html")



@app.route("/view_products")
def view_products():

    if "seller" not in session:
        return redirect("/seller_login")

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products WHERE seller_id=%s",(session["seller"],))
    products=cur.fetchall()

    return render_template("view_products.html",products=products)



# ------------------------------------------------
# SELLER VIEW ORDERS
# ------------------------------------------------

@app.route("/seller_orders")
def seller_orders():

    if "seller" not in session:
        return redirect("/seller_login")

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("""
    SELECT orders.*,products.name, buyers.name AS buyer
    FROM orders
    JOIN products ON products.id=orders.product_id
    JOIN buyers ON buyers.id=orders.buyer_id
    WHERE orders.seller_id=%s
    """,(session["seller"],))

    orders=cur.fetchall()

    return render_template("seller_orders.html",orders=orders)



@app.route("/approve_order/<id>")
def approve_order(id):

    conn=get_db()
    cur=conn.cursor()

    cur.execute("UPDATE orders SET status='approved' WHERE id=%s",(id,))
    conn.commit()

    return redirect("/seller_orders")



@app.route("/reject_order/<id>")
def reject_order(id):

    conn=get_db()
    cur=conn.cursor()

    cur.execute("UPDATE orders SET status='rejected' WHERE id=%s",(id,))
    conn.commit()

    return redirect("/seller_orders")


# ------------------------------------------------
# SELLER ANALYTICS
# ------------------------------------------------

@app.route("/seller_analytics")
def seller_analytics():

    if "seller" not in session:
        return redirect("/seller_login")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    seller_id = session["seller"]

    # -----------------------------------
    # MY PRODUCT SALES
    # -----------------------------------

    cur.execute("""
    SELECT products.name, COUNT(orders.id) AS sales
    FROM orders
    JOIN products ON products.id = orders.product_id
    WHERE products.seller_id=%s
    GROUP BY products.name
    """,(seller_id,))

    my_sales = cur.fetchall()


    # -----------------------------------
    # MY PRODUCT DEMAND
    # -----------------------------------

    cur.execute("""
    SELECT products.name, COUNT(interactions.product_id) AS demand
    FROM interactions
    JOIN products ON products.id = interactions.product_id
    WHERE products.seller_id=%s
    GROUP BY products.name
    """,(seller_id,))

    my_demand = cur.fetchall()


    # -----------------------------------
    # MARKET TRENDING PRODUCTS
    # -----------------------------------

    cur.execute("""
    SELECT products.name, COUNT(interactions.product_id) AS demand
    FROM interactions
    JOIN products ON products.id = interactions.product_id
    WHERE products.seller_id != %s
    GROUP BY products.name
    ORDER BY demand DESC
    LIMIT 5
    """,(seller_id,))

    market_trending = cur.fetchall()


    # -----------------------------------
    # LOCATION BASED MARKET TREND
    # -----------------------------------

    cur.execute("""
    SELECT buyers.location, COUNT(orders.id) AS demand
    FROM orders
    JOIN buyers ON buyers.id = orders.buyer_id
    JOIN products ON products.id = orders.product_id
    GROUP BY buyers.location
    ORDER BY demand DESC
    """)

    location_trend = cur.fetchall()


    # -----------------------------------
    # PRODUCT LOCATION DEMAND
    # -----------------------------------

    cur.execute("""
    SELECT 
    products.name AS product,
    buyers.location,
    COUNT(orders.id) AS demand
    FROM products
    JOIN orders ON products.id = orders.product_id
    JOIN buyers ON buyers.id = orders.buyer_id
    WHERE products.seller_id=%s
    GROUP BY products.name, buyers.location
    ORDER BY products.name, demand DESC
    """,(seller_id,))

    product_location = cur.fetchall()


    return render_template(
        "seller_analytics.html",
        my_sales=my_sales,
        my_demand=my_demand,
        market_trending=market_trending,
        location_trend=location_trend,
        product_location=product_location
    )
# ------------------------------------------------
# BUYER REGISTER
# ------------------------------------------------

@app.route("/buyer_register",methods=["GET","POST"])
def buyer_register():

    if request.method=="POST":

        name=request.form["name"]
        email=request.form["email"]
        mobile=request.form["mobile"]
        location=request.form["location"]
        age=request.form["age"]
        gender=request.form["gender"]
        username=request.form["username"]
        password=request.form["password"]

        conn=get_db()
        cur=conn.cursor()

        cur.execute("""
        INSERT INTO buyers
        (name,email,mobile,location,age,gender,username,password)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
        """,(name,email,mobile,location,age,gender,username,password))

        conn.commit()

        return redirect("/buyer_login")

    return render_template("buyer_register.html")



# ------------------------------------------------
# BUYER LOGIN
# ------------------------------------------------

@app.route("/buyer_login",methods=["GET","POST"])
def buyer_login():

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        conn=get_db()
        cur=conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM buyers WHERE username=%s AND password=%s",(username,password))
        buyer=cur.fetchone()

        if buyer:

            session["buyer"]=buyer["id"]

            return redirect("/buyer_dashboard")

    return render_template("buyer_login.html")



# ------------------------------------------------
# BUYER DASHBOARD
# ------------------------------------------------

@app.route("/buyer_dashboard")
def buyer_dashboard():

    if "buyer" not in session:
        return redirect("/buyer_login")

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products")
    products=cur.fetchall()

    return render_template("buyer_dashboard.html",products=products)



# ------------------------------------------------
# ADD TO CART
# ------------------------------------------------

@app.route("/add_to_cart/<id>")
def add_to_cart(id):

    if "buyer" not in session:
        return redirect("/buyer_login")

    conn=get_db()
    cur=conn.cursor()

    cur.execute("""
    INSERT INTO cart(buyer_id,product_id)
    VALUES(%s,%s)
    """,(session["buyer"],id))

    cur.execute("""
    INSERT INTO interactions(user_id,product_id,action)
    VALUES(%s,%s,'cart')
    """,(session["buyer"],id))

    conn.commit()

    return redirect("/cart")



# ------------------------------------------------
# VIEW CART
# ------------------------------------------------

@app.route("/cart")
def cart():

    if "buyer" not in session:
        return redirect("/buyer_login")

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("""
    SELECT cart.*,products.name,products.price,products.image
    FROM cart
    JOIN products ON products.id=cart.product_id
    WHERE buyer_id=%s
    """,(session["buyer"],))

    items=cur.fetchall()

    return render_template("cart.html",items=items)



# ------------------------------------------------
# PLACE ORDER
# ------------------------------------------------

@app.route("/place_order/<product_id>")
def place_order(product_id):

    if "buyer" not in session:
        return redirect("/buyer_login")

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products WHERE id=%s",(product_id,))
    product=cur.fetchone()

    cur.execute("""
    INSERT INTO orders(buyer_id,seller_id,product_id,price)
    VALUES(%s,%s,%s,%s)
    """,(session["buyer"],product["seller_id"],product_id,product["price"]))

    cur.execute("""
    INSERT INTO interactions(user_id,product_id,action)
    VALUES(%s,%s,'purchase')
    """,(session["buyer"],product_id))

    cur.execute("""
    DELETE FROM cart 
    WHERE buyer_id=%s AND product_id=%s
    """,(session["buyer"],product_id))

    conn.commit()

    return redirect("/buyer_orders")



# ------------------------------------------------
# BUYER ORDER HISTORY
# ------------------------------------------------

@app.route("/buyer_orders")
def buyer_orders():

    conn=get_db()
    cur=conn.cursor(dictionary=True)

    cur.execute("""
    SELECT orders.*,products.name,products.image
    FROM orders
    JOIN products ON products.id=orders.product_id
    WHERE buyer_id=%s
    """,(session["buyer"],))

    orders=cur.fetchall()

    return render_template("buyer_orders.html",orders=orders)



# ------------------------------------------------
# PAYMENT
# ------------------------------------------------

@app.route("/pay/<id>")
def pay(id):

    conn=get_db()
    cur=conn.cursor()

    cur.execute("UPDATE orders SET payment_status='paid' WHERE id=%s",(id,))
    conn.commit()

    return redirect("/buyer_orders")


class Config:

    def __init__(self):

        self.embedding_size = 128
        self.sequence_length = 50
        self.community_clusters = 10
        self.recommendation_top_k = 5


# --------------------------------------------------------
# DATA COLLECTION MODULE
# --------------------------------------------------------

class DataCollector:

    def __init__(self):
        self.customer_data = []
        self.product_data = []
        self.transaction_data = []

    def load_data(self):

        for i in range(100):

            self.customer_data.append({
                "customer_id": i,
                "location": "region_" + str(i % 5)
            })

        for i in range(50):

            self.product_data.append({
                "product_id": i,
                "category": "category_" + str(i % 6)
            })

        for i in range(200):

            self.transaction_data.append({
                "customer_id": np.random.randint(0,100),
                "product_id": np.random.randint(0,50)
            })


# --------------------------------------------------------
# GRAPH CONSTRUCTION
# --------------------------------------------------------

class GraphBuilder:

    def build_graph(self, transactions):

        edges = []

        for t in transactions:

            edges.append((t["customer_id"], t["product_id"]))

        return edges


# --------------------------------------------------------
# TENDGRAPHNET MODEL (GNN)
# --------------------------------------------------------

class TendGraphNet:

    def __init__(self, config):

        self.config = config
        self.embeddings = {}

    def train(self, graph_edges):

        for edge in graph_edges:

            node = edge[0]

            if node not in self.embeddings:

                self.embeddings[node] = np.random.rand(self.config.embedding_size)

    def get_embedding(self, node):

        return self.embeddings.get(node, np.zeros(self.config.embedding_size))


# --------------------------------------------------------
# COMMUNITY DETECTION
# --------------------------------------------------------

class CommunityDiscovery:

    def detect(self, embeddings):

        communities = {}

        for node, emb in embeddings.items():

            community_id = int(np.sum(emb) % 5)

            communities[node] = community_id

        return communities


# --------------------------------------------------------
# SEQBEHNET MODEL (SASRec)
# --------------------------------------------------------

class SeqBehNet:

    def __init__(self, config):

        self.config = config

    def train_sequences(self, transactions):

        sequences = {}

        for t in transactions:

            user = t["customer_id"]

            if user not in sequences:
                sequences[user] = []

            sequences[user].append(t["product_id"])

        return sequences

    def predict_next(self, sequence):

        predictions = []

        for i in range(self.config.recommendation_top_k):

            predictions.append(np.random.randint(0,50))

        return predictions


# --------------------------------------------------------
# DEMAND ANALYSIS
# --------------------------------------------------------

class DemandInsight:

    def analyze(self, transactions):

        demand = {}

        for t in transactions:

            pid = t["product_id"]

            if pid not in demand:
                demand[pid] = 0

            demand[pid] += 1

        return demand


# --------------------------------------------------------
# RECOMMENDATION ENGINE
# --------------------------------------------------------

class RecommendationEngine:

    def generate(self, community, seq_predictions):

        recommendations = []

        for p in seq_predictions:

            recommendations.append(p)

        return recommendations


# --------------------------------------------------------
# MAIN ANALYTICS PIPELINE
# --------------------------------------------------------

class PurchasingTendencyPipeline:

    def __init__(self):

        self.config = Config()

        self.collector = DataCollector()
        self.graph_builder = GraphBuilder()

        self.tend_graph = TendGraphNet(self.config)
        self.community_model = CommunityDiscovery()

        self.seq_model = SeqBehNet(self.config)
        self.demand_model = DemandInsight()

        self.recommender = RecommendationEngine()

    def run(self):

        self.collector.load_data()

        edges = self.graph_builder.build_graph(self.collector.transaction_data)

        self.tend_graph.train(edges)

        communities = self.community_model.detect(self.tend_graph.embeddings)

        sequences = self.seq_model.train_sequences(self.collector.transaction_data)

        demand = self.demand_model.analyze(self.collector.transaction_data)

        sample_user = 1

        seq_predictions = self.seq_model.predict_next(sequences.get(sample_user, []))

        community = communities.get(sample_user, 0)

        recommendations = self.recommender.generate(community, seq_predictions)

        result = {
            "user": sample_user,
            "community": community,
            "recommendations": recommendations
        }

        return result

# ------------------------------------------------
# AI RECOMMENDATIONS + MULTI-SHOP MAP
# ------------------------------------------------

@app.route("/recommendations")
def recommendations():

    if "buyer" not in session:
        return redirect("/buyer_login")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Step 1: Find top recommended product names by interaction score
    cur.execute("""
        SELECT p.name, COUNT(i.product_id) AS score
        FROM interactions i
        JOIN products p ON p.id = i.product_id
        GROUP BY p.name
        ORDER BY score DESC
        LIMIT 5
    """)

    top_products = cur.fetchall()

    product_names = [p["name"] for p in top_products]

    if not product_names:
        return render_template("recommendations.html", products=[])

    # Step 2: Get ALL sellers selling those products
    format_strings = ','.join(['%s'] * len(product_names))

    query = f"""
        SELECT 
            products.id,
            products.name,
            products.price,
            products.image,
            products.specification,

            sellers.shopname,
            sellers.address,
            sellers.latitude,
            sellers.longitude

        FROM products
        JOIN sellers ON sellers.id = products.seller_id

        WHERE products.name IN ({format_strings})
    """

    cur.execute(query, tuple(product_names))
    recs = cur.fetchall()

    return render_template("recommendations.html", products=recs)

@app.route("/seq")
def seq():

    if "buyer" not in session:
        return redirect("/buyer_login")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    buyer_id = session["buyer"]

    # --------------------------------
    # BUYER PURCHASE HISTORY
    # --------------------------------
    cur.execute("""
        SELECT products.id, products.name
        FROM orders
        JOIN products ON products.id = orders.product_id
        WHERE orders.buyer_id=%s
        ORDER BY orders.id DESC
    """, (buyer_id,))

    history = cur.fetchall()

    purchased_products = [h["name"] for h in history]

    if not history:
        conn.close()
        return render_template(
            "seq.html",
            purchased_products=[],
            products=[]
        )

    last_product = history[0]
    product_name = last_product["name"].lower()
    product_id = last_product["id"]

    # --------------------------------
    # ACCESSORY KEYWORDS
    # --------------------------------
    accessories = []

    if "mobile" in product_name or "phone" in product_name:
        accessories = ["case", "cover", "charger", "headphone", "earphone", "cable"]

    elif "laptop" in product_name or "macbook" in product_name:
        accessories = ["mouse", "keyboard", "bag", "cooling", "adapter"]

    elif "camera" in product_name:
        accessories = ["tripod", "lens", "memory", "card", "bag"]

    # --------------------------------
    # FIND ACCESSORY PRODUCTS
    # --------------------------------
    products = []

    if accessories:

        cur.execute("SELECT id, name, price, image, seller_id FROM products")
        all_products = cur.fetchall()

        for p in all_products:

            pname = p["name"].lower()

            if p["id"] == product_id:
                continue

            for word in accessories:
                if word in pname:
                    products.append(p)
                    break

    products = products[:6]

    conn.close()

    return render_template(
        "seq.html",
        purchased_products=purchased_products,
        products=products
    )

@app.route("/community2")
def community2():

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # --------------------------------
    # GET REAL PURCHASE DATA
    # --------------------------------
    cur.execute("""
        SELECT 
        buyers.location AS Location,
        sellers.category AS Product_Category,
        products.name AS Product_Name
        FROM orders
        JOIN buyers ON buyers.id = orders.buyer_id
        JOIN products ON products.id = orders.product_id
        JOIN sellers ON sellers.id = products.seller_id
    """)

    orders = cur.fetchall()

    conn.close()

    # --------------------------------
    # CONVERT ORDERS TO DATAFRAME
    # --------------------------------
    if orders:
        orders_df = pd.DataFrame(orders)

        # Add fake community label for new data
        orders_df["Community"] = "Live Buyers"

        # Merge dataset + live data
        combined = pd.concat([data, orders_df], ignore_index=True)

    else:
        combined = data.copy()

    # --------------------------------
    # COMMUNITY DISTRIBUTION
    # --------------------------------
    community = combined.groupby("Community").size()

    community_labels = list(community.index)
    community_values = list(community.values)

    # --------------------------------
    # PRODUCT CATEGORY DEMAND
    # --------------------------------
    category = combined.groupby("Product_Category").size()

    category_labels = list(category.index)
    category_values = list(category.values)

    # --------------------------------
    # LOCATION DEMAND
    # --------------------------------
    location = combined.groupby("Location").size()

    location_labels = list(location.index)
    location_values = list(location.values)

    # --------------------------------
    # PRODUCT POPULARITY
    # --------------------------------
    product = (
        combined.groupby("Product_Name")
        .size()
        .sort_values(ascending=False)
        .head(10)
    )

    product_labels = list(product.index)
    product_values = list(product.values)

    return render_template(
        "community2.html",
        community_labels=community_labels,
        community_values=community_values,
        category_labels=category_labels,
        category_values=category_values,
        location_labels=location_labels,
        location_values=location_values,
        product_labels=product_labels,
        product_values=product_values
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


app.run(debug=True)
