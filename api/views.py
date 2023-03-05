from flask import Blueprint, render_template,  jsonify, request, json, make_response, send_file, current_app as app
from . import db, decrypt, util, mail
from .models import *
from flask_login import login_user, current_user, logout_user, login_required
from functools import wraps
import csv, datetime, io, pdfkit
# import jwt
from openpyxl import Workbook
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required #use of flask-jwt-extended
import pandas as pd
from flask_mail import Message
from flask_cors import CORS, cross_origin
from flask.helpers import send_from_directory




#For print functions
import sys
#from sys import stderr

#Setting up the file as a blueprint
main = Blueprint("main", __name__, template_folder="template")

# Note that in the below code we static_folder will clash with the one introduced in the ini.py, hence we
# will have to refactor the code not to have two static folder locations
# main = Blueprint("main", __name__, static_folder="static", template_folder="template")

#Setting up login manager
from flask_login import LoginManager
login_manager = LoginManager()

methods=["POST", "GET", "PUT", "DELETE"]

@main.route('/')
@cross_origin()
def serve():
    return send_from_directory(app.static_folder, 'index.html')

# decorators
# def token_required(f):
#     @wraps(f)
#     def decorator(*args, **kwargs):
#         token = None
#         # if 'x-access-tokens' in request.headers:
#         #     token = request.headers['x-access-tokens']
#         if "Authorization" in request.headers:
#             token = request.headers["Authorization"].split()[1]
#         if not token:
#             return jsonify({'message': "a valid token is missing"})
#         try:
#             data = jwt.decode(token,"SECRET_KEY", algorithms =['HS256'])
#             current_user = User.query.filter_by(id=data['id']).first()
#         except:
#             return jsonify({'message': 'token is invalid'})

#         return f(*args, **kwargs)
#     return decorator

# def auth_required(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         auth = request.authorization
#         if auth and auth.username == 'username1' and auth.password == 'password':
#             return f(*args, **kwargs)
#         return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
#     return decorated

# @main.route('/t')
# def test():
#     if request.authorization and request.authorization.username == 'username' and request.authorization.password == 'password':
#         return '<h1>You are logged in!</h1>'
#     else:
#         return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
#     #return jsonify({'msg': "Hello World"})

# @main.route('page')
# @auth_required
# def page():
#     return '<h1>You are on page </h1>'

##The below functions used for the purpose of the tutorial
@main.route('/add_movie', methods = ["POST"])
def add_movie():
    movie_data = request.get_json()
    #new_movie = Movie(title=movie_data['title'], ratings=movie_data['ratings'])
    new_movie = Movie(**movie_data)
    db.session.add(new_movie)
    db.session.commit()
    print(new_movie)

    #return 'Done', 201
    return movie_schema.jsonify(new_movie)

@main.route('/movies')
def movies():
    movies_list = Movie.query.all()
    movies = movies_schema.dump(movies_list)
    #print(movies, file=sys.stderr)

    #return jsonify(movies)
    return jsonify({'movies': movies})

#Registration
@main.route('/register', methods=['POST'])
@cross_origin()
def register_user():
    user_data = request.get_json()
    username = user_data["user"]
    email = user_data["email"]
    check_username = User.query.filter_by(user=username).first()
    check_email = User.query.filter_by(email=email).first()
    if check_username:
        return make_response(jsonify({"msg":"Username Already Exists"}), 409)
        #return jsonify("Username Already Exists")
    elif check_email:
        return make_response(jsonify({"msg": "Email Already Exists"}), 409)

    #To hash the pass
    hashed_pwd = decrypt.generate_password_hash(user_data["pwd"]).decode('utf-8')
    user = User(user = username, email=email, pwd=hashed_pwd)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    res_data = {
            "msg": "User Added",
            "roles": "user"
        }
    return make_response(jsonify(res_data),201)

@main.route('/login',  methods=['POST'])
@cross_origin()
def login():
    user_data = request.get_json()
    username = user_data["user"]
    check_username = User.query.filter_by(user=username).first()

    if check_username and decrypt.check_password_hash(check_username.pwd, user_data["pwd"]):
        #Login Successfull
        login_user(check_username) # Sets the current user to the user provided

        #Creating a token with PyJWT --- Can create both access token and refresh token
        # token = jwt.encode(
        #     {
        #         "id" : check_username.id,
        #         'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=45)
        #     },
        #     "SECRET_KEY",
        #     algorithm='HS256'
        # )
        #Creating an access token with JWT-extended - default expire time == 15min
        access_token = create_access_token(identity=username)

        #Creating a refresh token with JWT-extended - default expore time == 30days
        refresh_token = create_refresh_token(identity = username)

        res_data = {
            "msg": "Login Successfull",
            "roles": [2001, 1984],
            # "token" : token,
            "access_token":access_token,
            "refresh_token": refresh_token
        }
        return make_response(jsonify(res_data), 201)
    else:
       return make_response(jsonify({'msg': "Invalid Username or Password"}), 409)


@main.route("/logout")
# @login_required
#@login_manager.user_loader
#@app.login_manager.user_loader
def logout():
    logout_user()
    return jsonify({'msg': "Logged Out"})

@main.route(('/getUsers'))
#@token_required ### Using pyPWT
@jwt_required() #Using jwt-extend (In this case only the access token required)
#@jwt_required(refresh=True) #Using jwt-extend --- Refresh token required
@cross_origin()
def get_users():
    users_list = User.query.all()
    users = users_schema.dump(users_list)

    return jsonify(users)

@main.route("/refresh")
@jwt_required(refresh=True)
@cross_origin()
def refresh():
    username = get_jwt_identity()
    access_token = create_access_token(identity=username)

    return jsonify({"token":access_token})

@main.route('/add_supplier', methods=["POST", "GET"])
@cross_origin()
def add_supplier():
    if request.method == "POST":
        supplier_data = request.get_json()
        supplier_data.pop("county")
        new_supplier = Supplier(**supplier_data)
        db.session.add(new_supplier)
        db.session.commit()
        print(new_supplier)

        return supplier_schema.jsonify(new_supplier)
    else:
        zones = util.get_zones()
        return jsonify({ "zones": zones })

@main.route('/suppliers', methods=["GET", "POST"])
@cross_origin()
def suppliers():
    if request.method == "GET":
        query_data = Supplier.query.all()
        suppliers = suppliers_schema.dump(query_data)

        return jsonify(suppliers)
    else:
        supplier_data = request.get_json()
        supplier_data.pop("county")
        new_supplier = Supplier(**supplier_data)
        db.session.add(new_supplier)
        db.session.commit()
        print(new_supplier)

        return supplier_schema.jsonify(new_supplier)

@main.route('/suppliers/<int:id>', methods=["GET", "POST", "PUT", "DELETE"])
@cross_origin()
def supplierDetail(id):
    supplier = Supplier.query.filter_by(id=id).first()
    if request.method == "GET":
        return jsonify(supplier_schema.dump(supplier))

    elif request.method == "PUT":
        supplier_data = request.get_json()
        for key, value in supplier_data.items():
            setattr(supplier, key, value)
        db.session.commit()

        return jsonify({'msg': "Supplier Details Updated"})
    elif request.method == "DELETE":
        db.session.delete(supplier)
        db.session.commit()
        return jsonify({'msg': "Delete function trigger"})

@main.route('/clients', methods=methods)
@cross_origin()
def clients():
    if request.method == "GET":
        query_clients = Client.query.all()
        clients =clients_schema.dump(query_clients)
        return jsonify(clients)

    elif request.method == "POST":
        client_data = request.get_json()
        client_data.pop("zone")
        new_client = Client(**client_data)
        db.session.add(new_client)
        db.session.commit()
        return client_schema.jsonify(new_client)

@main.route('/clients/<int:id>', methods=methods)
@cross_origin()
def clientDetail(id):
    client_query = Client.query.filter_by(id=id).first()
    if request.method == "GET":
        client = client_schema.dump(client_query)
        jobs_query = Job.query.filter_by(client_id=id).all()
        jobs = jobs_schema.dump(jobs_query)
        return jsonify({"client":client, "jobs":jobs})

    elif request.method == "PUT":
        client_data = request.get_json()
        for key, value in client_data.items():
            setattr(client, key, value)
        db.session.commit()
        return jsonify({'msg': "Client Details Updated"})

    elif request.method == "DELETE":
        db.session.delete(client)
        db.session.commit()
        return jsonify({'msg': "Delete function triggered"})

@main.route('/personnel/<int:id>', methods=["POST", "GET", "PUT", "DELETE"])
@cross_origin()
def personnel(id):
    company = Company.query.filter_by(id=id).first()
    persons_query = Person.query.filter_by(company_id=id)
    # persons_query = Person.query.with_parent(company)
    persons_query = company.personnel
    if request.method == "GET":
        persons = persons_schema.dump(persons_query)
        # print(persons)
        return jsonify(persons)

    #Retrieving and saving new person object
    elif request.method == "POST":
        person_data = request.get_json()
        person_data["company_id"] = id
        person = Person(**person_data)
        db.session.add(person)
        db.session.commit()
        return jsonify({"msg": "Person Saved"})

    #Updating a person object
    elif request.method == "PUT":
        person_data = request.get_json()
        p_id = person_data["id"]
        person = persons_query.filter_by(id=p_id).first()

        for key, value in person_data.items():
            setattr(person, key, value)
        db.session.commit()

        # return person_schema.jsonify(person)
        return jsonify({"msg": "Person Updated"})

    elif request.method == "DELETE":
        p_id = request.get_json()
        person = persons_query.filter_by(id=p_id).first()
        db.session.delete(person)
        db.session.commit()
        return jsonify({"msg": "Person Deleted"})

@main.route("/products", methods=["POST", "GET", "PUT", "DELETE"])
@cross_origin()
def products():
    # print(request.get_json())
    # Retrieving list of products from the database
    if request.method == "GET":
        products_query = Product.query.all()
        # products = products_schema.dump(products_query)
        products = []
        for product in products_query:
            price = product.prices.order_by(Price.price.desc()).first()
            p = product_schema.dump(product) | price_schema.dump(price)
            products.append(p)

        return jsonify(products)

    #Posting a new product to the database
    elif request.method == "POST":
        print(request.get_json())
        request_data = request.get_json()
        price = request_data.pop("price")
        s_id = request_data.pop("supplier")
        #Creating new product item
        product = Product(**request_data)

        #Creating new price item
        # price = Price(price=price, supplier_id=s_id, product_id=product.id)
        price = Price(price=price, supplier_id=s_id)
        product.prices.append(price)
        db.session.add(product)
        db.session.add(price)
        db.session.commit()

        return jsonify("Product Added")

@main.route('/products/<int:id>', methods=methods)
@cross_origin()
def productDetails(id):
    product = Product.query.filter_by(id=id).first()
    price = product.prices
    if request.method == "GET":
        p = product_schema.dump(product)
        pr = prices_schema.dump(price)

        return jsonify({"product":p, "prices":pr})

    elif request.method == "PUT":
        request_data = request.get_json()
        for key, value in request_data.items():
            setattr(product, key, value)
        db.session.commit()
        return jsonify(request_data)

    elif request.method  == "DELETE":
        db.session.delete(product)
        db.session.commit()
        #incase of session.query().filter().delete() -- on the parent and child model use "passive_deletes" $ "ondelete"
        return jsonify({"msg": "Product Deleted"})

@main.route('/prices/<int:id>', methods = methods)
@cross_origin()
def prices(id):
    #The below line gives a single query object
    result = Product.query.join(Price, Product.id == Price.product_id).filter(Price.supplier_id == id).all()
    #The below code will give the results in form of a two query objects inside a tuple
    result1 = db.session.query(Product, Price).join(Price).filter(Price.supplier_id == id)
    #The below code will give the results in form of a two query objects inside a tuple
    result2 = db.session.query(Product, Price).outerjoin(Price, Product.id == Price.product_id).filter(Price.supplier_id == id).all()

    #creating empty product list
    products = []

    # Converting the result to dictionary
        # for p in result:
        #     pd = product_schema.dump(p) | price_schema.dump(p.prices[0])
        #     products.append(pd)
        # print(products)

    # Converting result 2 to dictionary
    for p, pr in result1.all():
        dic = product_schema.dump(p) | price_schema.dump(pr)
        products.append(dic)

    if request.method == "GET":
        return jsonify(products)
    elif request.method == "POST":
        request_data = request.get_json()
        print(request_data)
        product = Product.query.filter_by()
        supplier = Supplier.query.filter_by()
        price = Price(**request_data)
        # price = Price(price=price, supplier_id=data, product_id=product.id)
        # price = Price(price=price, supplier_id=s_id)
        # product.prices.append(price)
        # db.session.add(product)
        print(price)
        db.session.add(price)
        db.session.commit()
        return price_schema.jsonify(price)

    elif request.method == "PUT":
        product_data = request.get_json()
        price_id = product_data["id"]
        price = Price.query.filter_by(id=price_id).first()

        for key, value in product_data.items():
            setattr(price, key, value)
        db.session.commit()

        return jsonify("Price Updated Successful")
    # Deleting the price item
    else:
        price_id = request.get_json()
        product_price =  result1.filter(Price.id == price_id).first()
        price = product_price[1]
        prices = product_price[0].prices.all()

        #note price cannot be deleted if no other prices exist for the product
        if len(prices)>1:
            db.session.delete(price)
            db.session.commit()
            return jsonify("Delete")
        else:
            return jsonify("Retain")

@main.route('/jobs', methods=methods)
@cross_origin()
def jobs():
    if request.method == "GET":
        query_jobs = Job.query.all()
        jobs = jobs_schema.dump(query_jobs)
        return jsonify(jobs)

    elif request.method == "POST":
        # Job.__table__.drop(db.engine) --To drob a table
        print(request)
        request_data = request.get_json()
        print(request_data)
        # job = Job(**request_data)
        job = Job(code = request_data["code"], client_id = request_data["client_id"])
        # job = Job(code = request_data["code"], client_id = request_data["client_id"], value=0, lpo=0, cheque=0)
        print(job)
        db.session.add(job)
        db.session.commit()
        return job_schema.jsonify(job)

@main.route('/jobs/<int:id>', methods=methods)
@cross_origin()
def jobDedatils(id):
    job_query = Job.query.filter_by(id=id).first()
    util.createNotes(job_query)

    #Querying for the Supply and Product
    ps_query = db.session.query(Product, Supply).join(Supply).filter(Supply.job_id == id)
    supplies = []
    #Merging the Supplies & Products
    for p, s in ps_query.all():
        dic = product_schema.dump(p) | supply_schema.dump(s)
        supplies.append(dic)

    if request.method == "GET":
        if(job_query):
            job = job_schema.dump(job_query)
            return jsonify({"msg":"Valid Job Id", "job":job, "supplies":supplies})
        else:
            return jsonify({"msg":"Invalid"})
    elif request.method == "POST":
        request_data = request.get_json()
        # request_data.pop("id")
        # product = Product.query.filter_by(id = request_data["product_id"])
        # minBuying = product.prices.order_by(Price.price.asc()).first()
        prices = Price.query.filter_by(product_id=request_data["product_id"])
        minBuying = prices.order_by(Price.price.asc()).first()
        supply = Supply(
            qty = request_data["qty"],
            price = request_data["price"],
            minBuying = minBuying.id,
            maxBuying = request_data["maxBuying"],
            total = request_data["total"],
            product_id = request_data["product_id"],
            job_id = id,
        )

        db.session.add(supply)
        db.session.commit()
        job_value = util.updateJobValue(id)
        job_query = Job.query.filter_by(id = id).first()
        job_query.value = job_value
        db.session.commit()




        return  jsonify(job_query.value)
    elif request.method == "PUT":
        request_data = request.get_json()
        for key, value in request_data.items():
            if key == "lpo" or key == "cheque":
                setattr(job_query, key, int(value))
            else:
                setattr(job_query, key, value)
        db.session.commit()

        return job_schema.jsonify(job_query)

    elif request.method == "DELETE":
        db.session.delete(job_query)
        db.session.commit()

        return jsonify("Delete")

@main.route("/supplies/<int:id>", methods=methods)
@cross_origin()
def supplies(id):
    # supplies_query = Supply.query.all()
    # if request.method == "GET":
    #     supplies = supplies_schema.dump(supplies_query)
    #     return jsonify(supplies)
    supply_query = Supply.query.filter_by(id=id).first()
    if request.method == "PUT":
        request_data = request.get_json()
        print(request_data)
        supply_query.price = request_data["price"]
        supply_query.qty = request_data["qty"]
        supply_query.total = request_data["total"]
        db.session.commit()
        job_value = util.updateJobValue(supply_query.job_id)
        job_query = Job.query.filter_by(id = supply_query.job_id).first()
        job_query.value = job_value
        db.session.commit()

        return jsonify(job_schema.dump(job_query))

    elif request.method == "DELETE":
        db.session.delete(supply_query)
        db.session.commit()
        job_value = util.updateJobValue(supply_query.job_id)
        job_query = Job.query.filter_by(id = supply_query.job_id).first()
        job_query.value = job_value

        db.session.commit()
        return jsonify({"msg":"Delete", "value":job_value})


@main.route('/get_variables')
@cross_origin()
def get_variables():
    data = util.get_data()
    return jsonify(data)

@main.route('/get_counties')
@cross_origin()
def get_counties():
    data = util.get_county()
    return jsonify(data)

@main.route('/generate_docs/<int:id>/<string:slug>')
@cross_origin()
def generateDocs(id, slug):
    print(slug)
    job_query = Job.query.filter_by(id=id).first()
    notes_query = Note.query.filter_by(job_id=id).first()
    notes = {} if not notes_query else note_schema.dump(notes_query)

    client_query = Client.query.filter_by(id = job_query.client_id).first()
    job = job_schema.dump(job_query) | client_schema.dump(client_query)

     #Querying for the Supply and Product
    def priceQuery(id):
        price = Price.query.filter_by(id=id).first()
        return price.price

    product_list = []
    ps_query = db.session.query(Product, Supply).join(Supply).filter(Supply.job_id == id)
    remove_list = ['description', 'weight', 'id', 'size', 'category', 'product_id', 'job_id']
    supplies_full = []
    supplies = []
    #Merging the Supplies & Products
    for p, s in ps_query.all():
        dic = product_schema.dump(p) | supply_schema.dump(s) | {"minBuying":priceQuery(s.minBuying), "maxBuying":priceQuery(s.maxBuying),  "total_buying": s.qty * priceQuery(s.minBuying)}
        supplies.append({key: dic[key] for key in dic if key not in remove_list})
        product_list.append(p.id)
        supplies_full.append(dic)

    column_heads = list(supplies[0].keys())
    # Setting up a context libraries that contains our data
    context = {
        "job": job,
        "supplies":supplies,
        "notes": notes
    }

    #Getting the current time
    now = datetime.datetime.now()
    # format the current time as a string in the format dd/mm/yyyy
    formatted_time = now.strftime('%d/%m/%Y')
    #Generating the file name
    filename = f"{job_query.code}-{formatted_time}"

    # Generating a csv file
    if slug == "csv":
        # Creating the csv while iterating the dictionary
        with open('dict.csv', "w", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(column_heads)
            # writer.writerow(['brand', 'name', 'qty', 'price', 'maxBuying', 'total', 'minBuying', 'total_buying']) #To get proper placement we can feed a list of headers manually
            total_buying = 0
            total_selling = 0
            for s in supplies:
                writer.writerow(list(s.values()))
                # writer.writerow([s['brand'], s['name'], s['qty'], s['price'] ...etc] )
                total_buying += (s["minBuying"]* s["qty"])
                total_selling += s["total"]
            writer.writerow(["","", "", "Grand Total", total_selling, "","", total_buying, "Difference",(total_selling-total_buying)])

        return send_file('../dict.csv',
                    mimetype='text/csv',
                    download_name=f"{filename}.{slug}",
                    as_attachment=True
                )

    #Creating the csv using pandas from a dict
    # df = pd.DataFrame(supplies)
        # df[["name", "brand", "qty", "minBuying", "maxBuying","price","total_buying","total"]].to_csv("trial1.csv", index=False)

        #Creating the csv with csv writer -- With this naming convetion it overwrites file with similar name
        # with open('dict.csv', "w", newline="") as csvfile:
        #     writer = csv.DictWriter(csvfile, fieldnames=column_heads)
        #     writer.writeheader()
        #     writer.writerows(supplies)
        
    #Creating with query -- not working(for future reference)
        # print(job_query[0].keys())
        # fh = open('data.csv', 'wb')
        # outcsv = csv.writer(fh)
        # # outcsv.writerow(job_query[0].keys())
        # outcsv.writerow(job_query)
        # fh.close()


        # return .....
    
    elif slug == "xlsx":
        #Creating an Excel Workbook
        wb = Workbook()
        ws = wb.active

        #Adding Column headers
        ws.append(['brand', 'name', 'qty', 'price', 'total', 'maxBuying', 'minBuying', 'total_buying'])

        #Adding Data
        total_buying = 0
        total_selling = 0
        for s in supplies:
            data = [s['brand'], s['name'], s['qty'], s['price'], s['total'], s['maxBuying'], s['minBuying'], s['total_buying']]
            # data = list(s.values())
            ws.append(data)
            total_buying += (s["minBuying"]* s["qty"])
            total_selling += s["total"]
        # Add summary
        summary = ["", "", "", "Grand Total", total_selling, "", "", total_buying, "Difference", (total_selling-total_buying)]
        ws.append(summary)

        # Set response headers --- In this case we do not use the buffer 
        # response = make_response(wb.save_as_stream())
        # response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        # response.headers['Content-Disposition'] = 'attachment; filename=filename'

        # return response


        # Saving the workbook to a buffer 
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Create a response and send the buffer as a file download
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{filename}.{slug}",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    elif slug == 'email':
        #Creating an empty dictionary, where the key will be the supplier and the products the value
        result = {} 
        for id in product_list:
            prices = Price.query.filter_by(product_id=id)
            for price in prices:
                #looping through the prices to get the supplier id
                supplier_id = price.supplier_id
                if supplier_id not in result:
                    #For each supplier check if a corresponding key exist in result, 
                    # if not creat a key with an empty list value
                    result[supplier_id] = []
                #Next append the product id to the created list 
                result[supplier_id].append(id)

        # Convert the dictionary to a list of dictionaries
        output = [{"supplier": k, "products": v} for k, v in result.items()]

        for k, v in result.items():
            supplier = Supplier.query.filter_by(id=k).first()
            supplys = [
                dic for dic in supplies_full if dic['product_id'] in v
            ]

            # Creating an Excel Workbook
            wb = Workbook()
            ws = wb.active
            column_names = [ 'name', 'brand', 'qty', 'price', 'total']
            # Writing the heading
            ws.append(column_names)
            # Adding the rows
            for s in supplys:
                ws.append([s['name'], s['brand'], s['qty']])
            # Saving the workbook to a buffer 
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            msg = Message('Bulk!', recipients=['kevin.mutinda.ck@gmail.com'])
            msg.body = 'Hello From Flask'
            msg.attach(
                    filename='invoice.xlsx',
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    data=buffer.getvalue()
                )
            mail.send(msg)

        return jsonify("Email Sent")
        

    elif slug == 'pdf':
        context = {"msg":"Hello 23"}
        response = util.printPdf(context)

        return response

    elif slug == 'rfq':
        # context = {"msg":"Hello 23", "type":slug}
        a = [{"title":"RFQ", "body":"Quotation for RFQ"}]
        response = util.printPdf(context, a)

        return response
    elif slug == "di":
        job_query.status = "Supplied"
        db.session.commit()
        a = [{"title":"Invoice", "body":"Invoice"}, {"title":"Delivery", "body":"Delivery Note"}]
        response = util.printPdf(context)

        return response

    elif slug == "receipt":
        a = [{"title":"Receipt", "body":"Receipt"}]
        response = util.printPdf(context, a)

        return response

    
        
@main.route('/mail')
@cross_origin()
def send_mail():
    mails = ['cayapo5476@wireps.com', 'pucyxy@teleg.eu']
    with mail.connect() as conn:
        for email in mails:
            msg = Message('Bulk!', recipients=[email])
            msg.body = 'Hello From Flask'
            conn.send(msg)

    return 'Message sent'


        






