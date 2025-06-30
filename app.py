from flask import Flask, render_template, request, redirect, session, url_for,jsonify,flash
from bson.objectid import ObjectId
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import uuid
import random
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
app = Flask(__name__)
app.secret_key = '584e6e31e50ccb19e9c09ecee1e9e6712bba7334fbea2489507d880cc76385fa'  # Use a strong secret key in production


# AWS Setup using IAM Role
REGION = 'ap-south-1'  # Replace with your actual AWS region
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns_client = boto3.client('sns', region_name=REGION)

users_table = dynamodb.Table('travelgo_users')
trains_table = dynamodb.Table('trains')
bookings_table = dynamodb.Table('bookings')

SNS_TOPIC_ARN = 'arn:aws:sns:ap-south-1:353250843450:TravelGoBookingTopic'  # Replace with actual SNS topic ARN

def send_sns_notification(subject, message):
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except Exception as e:
        print(f"SNS Error: {e}")


def send_sns_notification(subject, message):
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except Exception as e:
        print(f"SNS Error: {e}")

# --- Dummy Data (In a real app, these would come from your database) ---
# This is just for demonstration, as we're not persisting bus/train availability yet.
# For actual seat selection, you'd query specific journey's seat data.
dummy_bus_train_data = {
    "Hyderabad_Vijayawada_Orange Travels_08:00 AM": { # Example unique ID for a journey
        "total_seats": 30,
        "booked_seats": ["A1", "A2", "B3"] # Example: These seats are already booked
    },
    "Hyderabad_Vijayawada_Andhra Pradesh Express_06:00": {
        "total_seats": 50,
        "booked_seats": ["C5", "C6", "D1"]
    }
    # Add more entries for other unique bus/train journeys
}
# Dummy bus data for selection and confirmation
dummy_buses = [
    {
        "busId": "bus_001",
        "name": "Orange Travels",
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "time": "08:00 AM",
        "type": "AC Sleeper",
        "price": 500
    },
    {
        "busId": "bus_002",
        "name": "TSRTC Express",
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "time": "10:00 AM",
        "type": "Non AC Seater",
        "price": 350
    },
    {
        "busId": "bus_003",
        "name": "Morning Star",
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "time": "02:00 PM",
        "type": "AC Sleeper",
        "price": 550
    }
]
# Dummy flight data for selection and confirmation
dummy_flights = [
    {
        "flightId": "flight_001",
        "name": "IndiGo ",
        "flight_no": "6E 123",
        "source": "Hyderabad",
        "destination": "Delhi",
        "departure_time": "09:00",
        "arrival_time": "11:30",
        "type": "Economy",
        "price": 3500
    },
    {
        "flightId": "flight_002",
        "name": "AirIndia",
        "flight_no": "AI 456",
        "source": "Hyderabad",
        "destination": "Mumbai",
        "departure_time": "13:45",
        "arrival_time": "15:30",
        "type": "Business",
        "price": 6200
    },
    {
        "flightId": "flight_003",
        "name": "SpiceJet",
        "flight_no": "SG 789",
        "source": "Bengaluru",
        "destination": "Kolkata",
        "departure_time": "07:00",
        "arrival_time": "10:15",
        "type": "Economy",
        "price": 4200
    }
]


# --- End Dummy Data ---

# Home route
@app.route('/')
def home():
    logged_in = 'email' in session
    return render_template('home.html', logged_in=logged_in)

# User registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # handle registration (email, username, password)
        return redirect(url_for('login'))
    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user=users_table.find_one({"email":email})
        
        if user and check_password_hash(user['hashed_password'], password):
            session['email'] = email
            session['username'] = user['username']
            users_table.update_one({"email":email},{"$inc":{"login_count":1}}) 
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials'
            return render_template('login.html', error=error)
    return render_template('login.html')

# Dashboard route (no bookings shown here)
from bson.objectid import ObjectId

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    raw_bookings = list(db.bookings.find({'user_email': session['email']}))
    bookings = []

    for b in raw_bookings:
        booking_type = b.get('type', 'flight')

        if booking_type == 'hotel':
            bookings.append({
                '_id': str(b.get('_id')),
                'booking_type': booking_type,
                'hotel_name': b.get('hotel_name', 'Unknown Hotel'),
                'location': b.get('location', ''),
                'checkin_date': b.get('checkin_date', 'N/A'),
                'checkout_date': b.get('checkout_date', 'N/A'),
                'room_type': b.get('room_type', ''),
                'num_rooms': b.get('num_rooms', 1),
                'num_nights': b.get('num_nights', 1),
                'total_price': b.get('total_price', 0),
                'booking_date': b.get('booking_date', ''),
            })
        else:
            flight_class = b.get('class') or b.get('flight_class') or ''
            bookings.append({
                '_id': str(b.get('_id')),
                'booking_type': booking_type,
                'name': b.get('name') or b.get('airline') or 'Unknown',
                'source': b.get('source', ''),
                'destination': b.get('destination', ''),
                'travel_date': b.get('travel_date') or b.get('date') or 'N/A',
                'time': b.get('time', 'N/A'),
                'num_persons': b.get('num_persons') or b.get('passengers') or 1,
                'total_price': b.get('total_price', 0),
                'class': flight_class,
                'booking_date': b.get('booking_date', ''),
                'selected_seats': b.get('selected_seats', [])
            })

    return render_template('dashboard.html', bookings=bookings)


# Separate Bookings page route
@app.route('/bookings', methods=['GET', 'POST'])
def bookings():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Handle booking cancellation on POST
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        if booking_id:
            from bson.objectid import ObjectId
            db.bookings.delete_one({'_id': ObjectId(booking_id), 'user_email': session['email']})
            # You can flash a message or redirect here
            return redirect(url_for('bookings'))

    # Fetch bookings for this user
    raw_bookings = list(db.bookings.find({'user_email': session['email']}))

    # Format bookings for template
    bookings = []
    for b in raw_bookings:
        booking_type = b.get('booking_type') or b.get('type') or 'flight'  # adjust to your data

        if booking_type == 'hotel':
            bookings.append({
                '_id': str(b.get('_id')),
                'booking_type': 'hotel',
                'hotel_name': b.get('hotel_name', 'Unknown Hotel'),
                'location': b.get('location', ''),
                'checkin_date': b.get('checkin_date', 'N/A'),
                'checkout_date': b.get('checkout_date', 'N/A'),
                'room_type': b.get('room_type', ''),
                'num_rooms': b.get('num_rooms', 1),
                'num_nights': b.get('num_nights', 1),
                'total_price': b.get('total_price', 0),
            })
        else:
            bookings.append({
                '_id': str(b.get('_id')),
                'booking_type': booking_type,
                'name': b.get('name') or b.get('airline') or 'Unknown',
                'source': b.get('source', ''),
                'destination': b.get('destination', ''),
                'travel_date': b.get('travel_date') or b.get('date') or 'N/A',
                'time': b.get('time', 'N/A'),
                'num_persons': b.get('num_persons') or b.get('passengers') or 1,
                'total_price': b.get('total_price', 0),
                'class': b.get('class') or b.get('flight_class') or '',
                'selected_seats': b.get('selected_seats', None),
            })
            print("Bookings for user:", session['email'], raw_bookings)


    return render_template('bookings.html', bookings=bookings)


@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if 'email' not in session:
        return redirect(url_for('login'))

    booking_id = request.form.get('booking_id')
    if booking_id:
        bookings_collection.delete_one({'_id': ObjectId(booking_id)})
        flash('Booking cancelled successfully.', 'success')
    else:
        flash('Booking ID missing.', 'danger')

    return redirect(url_for('dashboard'))




# Handle AJAX JSON posting - separate POST view
@app.route('/add_to_wishlist_json', methods=['POST'])
def add_to_wishlist_json():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    if not request.is_json:
        return jsonify({'success': False, 'message': 'Content-Type must be application/json'}), 415

    data = request.get_json()
    if not data.get('item_name') or not data.get('item_details'):
        return jsonify({'success': False, 'message': 'Missing fields'}), 400

    wishlist_col.insert_one({
        'email': session['email'],
        'item_id': data['item_name'],  # or a unique ID
        'item_name': data['item_name'],
        'item_details': data['item_details'],
        'item_image': data.get('item_image', ''),
        'added_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })
    return jsonify({'success': True, 'message': 'Item added to wishlist'})


@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('wishlist.html')

@app.route('/wishlist_data')
def wishlist_data():
    if 'email' not in session:
        return jsonify({'wishlist': []})
    items = list(wishlist_col.find({'email': session['email']}, {'_id': 0}))
    return jsonify({'wishlist': items})

@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    item_id = request.json.get('item_id')
    if not item_id:
        return jsonify({'success': False, 'message': 'Item ID not provided'})

    wishlist_col.delete_one({'email': session['email'], 'item_id': item_id})
    return jsonify({'success': True, 'message': 'Item removed from wishlist'})

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()  # Clear all user session data
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))


# ---------------- Booking Routes ----------------
@app.route('/book_bus')
def book_bus():
    return render_template('bus.html')

@app.route('/confirm_bus_details', methods=['GET', 'POST'])
def confirm_bus_details():
    if 'email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'GET':
        name = request.args.get('name')
        bus_type = request.args.get('type')
        source = request.args.get('source')
        destination = request.args.get('destination')
        travel_date = request.args.get('date')
        time = request.args.get('time')
        price_per_person = float(request.args.get('price', 0))
        num_persons = int(request.args.get('persons', 1))

        # Check for missing values
        if not all([name, bus_type, source, destination, travel_date, time]):
            flash("Incomplete booking details. Please go back and search again.")
            return redirect(url_for('book_bus'))  # Replace with your bus search route

        booking = {
            "name": name,
            "type": bus_type,
            "source": source,
            "destination": destination,
            "travel_date": travel_date,
            "time": time,
            "num_persons": num_persons,
            "price_per_person": price_per_person,
            "total_price": price_per_person * num_persons,
        }

        booked_seats = ["A1", "A3", "B2"]  # Dummy list
        return render_template('confirm_bus_details.html', booking=booking, booked_seats=booked_seats)


    # POST method: handle booking confirmation form submission
    if request.method == 'POST':
        # Get form fields
        name = request.form.get('name')
        source = request.form.get('source')
        destination = request.form.get('destination')
        time = request.form.get('time')
        bus_type = request.form.get('type')
        price_per_person = float(request.form.get('price', 0))
        travel_date = request.form.get('date')
        num_persons = int(request.form.get('persons', 1))
        selected_seats_str = request.form.get('selected_seats', '')
        selected_seats = selected_seats_str.split(',') if selected_seats_str else []

        total_price = price_per_person * len(selected_seats)

        booking_doc = {
            "user_email": session['email'],
            "name": name,
            "source": source,
            "destination": destination,
            "time": time,
            "type": bus_type,
            "price_per_person": price_per_person,
            "travel_date": travel_date,
            "num_persons": num_persons,
            "selected_seats": selected_seats,
            "total_price": total_price,
            "booking_date": datetime.utcnow()
        }

        # Save booking to DB
        bookings_collection.insert_one(booking_doc)

        flash(f"Booking confirmed with seats: {', '.join(selected_seats)}")

        # Redirect to bookings page after successful booking
        return redirect(url_for('bookings'))

@app.route('/final_confirm_booking', methods=['POST'])
def final_confirm_booking():
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    selected_seats = request.form.get('selected_seats', '')

    booking = session.pop('pending_booking', None)

    if not booking or not selected_seats:
        flash("Booking failed! Missing data.", "error")
        return redirect(url_for("dashboard"))

    # Prevent double booking: scan for existing seats with same travel_date & transport ID
    response = bookings_table.scan(
        FilterExpression=Key('travel_date').eq(booking['travel_date']) & 
                         Key('item_id').eq(booking['item_id'])  # item_id = bus/train/flight + date
    )

    existing = set()
    for b in response.get('Items', []):
        if 'seats_display' in b:
            existing.update(b['seats_display'].split(', '))

    selected = selected_seats.split(', ')
    if any(s in existing for s in selected):
        flash("One or more selected seats are already booked!", "error")
        return redirect(url_for("dashboard"))

    # Save confirmed booking
    booking['seats_display'] = selected_seats
    booking['user_email'] = user_email
    booking['booking_id'] = str(uuid.uuid4())
    booking['booking_date'] = datetime.now().isoformat()

    bookings_table.put_item(Item=booking)

    send_sns_notification(
        subject=f"{booking['booking_type'].capitalize()} Booking Confirmed",
        message=f"Your {booking['booking_type']} from {booking['source']} to {booking['destination']} on {booking['travel_date']} is confirmed.\nSeats: {booking['seats_display']}\nTotal: ₹{booking['total_price']}"
    )

    flash(f"{booking['booking_type'].capitalize()} booking confirmed!", 'success')
    return redirect(url_for('dashboard'))



@app.route('/book_train')
def book_train():
    return render_template('train.html')

# Add this route to handle POST booking confirmation with seats:
@app.route('/final_confirm_train_booking', methods=['POST'])
def final_confirm_train_booking():
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    selected_seats = request.form.get('selected_seats', '')
    selected_seats_list = selected_seats.split(',') if selected_seats else []

    booking = session.get('pending_booking')
    if not booking:
        flash("Booking session expired. Please try again.")
        return redirect(url_for('book_train'))

    booking['user_email'] = user_email
    booking['price_per_person'] = booking.get('price_per_person', 0)
    booking['total_price'] = len(selected_seats_list) * booking['price_per_person']
    booking['booking_type'] = 'train'
    booking['booking_id'] = str(uuid.uuid4())
    booking['booking_date'] = datetime.now().isoformat()
    booking['seats_display'] = ''

    # SCAN the bookings table to find other bookings with the same train_number and travel_date
    response = bookings_table.scan(
        FilterExpression=Key('train_number').eq(booking['train_number']) & Key('travel_date').eq(booking['travel_date'])
    )

    booked_seats = set()
    for b in response.get('Items', []):
        if 'seats_display' in b:
            booked_seats.update(b['seats_display'].split(', '))

    # Generate and allocate seats
    all_seats = [f"S{i}" for i in range(1, 101)]
    available_seats = [seat for seat in all_seats if seat not in booked_seats]

    if len(available_seats) < len(selected_seats_list):
        flash("Not enough seats available. Please try another train or date.")
        return redirect(url_for('book_train'))

    allocated_seats = random.sample(available_seats, len(selected_seats_list))
    booking['seats_display'] = ', '.join(allocated_seats)

    # Save to DynamoDB
    bookings_table.put_item(Item=booking)

    session.pop('pending_booking', None)

    send_sns_notification(
        subject="Train Booking Confirmed",
        message=f"Train {booking['train_number']} from {booking['source']} to {booking['destination']} on {booking['travel_date']} is confirmed.\nSeats: {booking['seats_display']}\nTotal: ₹{booking['total_price']}"
    )

    flash(f"Train booking confirmed successfully! Seats: {booking['seats_display']}")
    return redirect(url_for('bookings'))



# Modify your existing /confirm_train_details route to only render template with GET:
@app.route('/confirm_train_details')
def confirm_train_details():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Read all train details from query parameters
    name = request.args.get('name')
    train_no = request.args.get('trainNo')
    source = request.args.get('source')
    destination = request.args.get('destination')
    time = request.args.get('time')
    arrival_time = request.args.get('arrivalTime')
    train_type = request.args.get('type')
    price_per_person = float(request.args.get('price'))
    travel_date = request.args.get('date')
    num_persons = int(request.args.get('persons'))

    # Store in session pending booking to use later when confirming
    booking_details = {
        'name': name,
        'train_no': train_no,
        'source': source,
        'destination': destination,
        'time': time,
        'arrival_time': arrival_time,
        'type': train_type,
        'price_per_person': price_per_person,
        'travel_date': travel_date,
        'num_persons': num_persons,
        'booking_type': 'train'
    }
    session['pending_booking'] = booking_details

    return render_template('confirm_train_details.html', booking=booking_details)

@app.route('/book_flight')
def book_flight():
    return render_template('flight.html')


@app.route('/confirm_flight_details', methods=['GET', 'POST'])
def confirm_flight_details():
    if request.method == 'GET':
        if 'email' not in session:
            flash("Please log in")
            return redirect(url_for('login'))

        booking = {
            'name': request.args.get('name', 'Unknown Flight'),
            'flight_no': request.args.get('flight_no', ''),
            'source': request.args.get('source', ''),
            'destination': request.args.get('destination', ''),
            'departure_time': request.args.get('departure_time', ''),
            'arrival_time': request.args.get('arrival_time', ''),
            'class': request.args.get('class', ''),
            'price_per_person': float(request.args.get('price', 0)),
            'travel_date': request.args.get('travel_date', ''),
            'num_persons': int(request.args.get('num_persons', 1)),
        }
        session['pending_booking'] = booking
        return render_template('confirm_flight_details.html', booking=booking)

    # POST action (on booking confirmation)
    selected_seats = request.form.get('selected_seats', '').split(',')
    booking = session.pop('pending_booking', None)
    if not booking:
        flash("Session expired, please start again.")
        return redirect(url_for('book_flight'))

    booking.update({
        'selected_seats': selected_seats,
        'user_email': session['email'],
        'total_price': len(selected_seats) * booking['price_per_person'],
        'booking_type': 'flight'
    })
    db.bookings.insert_one(booking)
    flash(f"Flight confirmed: {booking['name']}, Seats: {', '.join(selected_seats)}")
    return redirect(url_for('bookings'))



@app.route('/book_hotel')
def book_hotel():
    return render_template('hotel.html')

@app.route('/confirm_hotel_details', methods=['GET', 'POST'])
def confirm_hotel_details():
    if 'email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.form.to_dict()

        # Ensure proper room_type exists (can be "Deluxe", "VIP", etc.)
        room_type = data.get('room_type', 'Standard')

        booking = {
            'booking_type': 'hotel',  # 🔄 was 'type'
            'user_email': session['email'],
            'hotel_name': data['hotel_name'],
            'location': data['location'],
            'checkin_date': data['checkin_date'],
            'checkout_date': data['checkout_date'],
            'num_rooms': int(data['num_rooms']),
            'num_guests': int(data['num_guests']),
            'price_per_night': int(data['price']),
            'room_type': room_type,
            'total_price': int(data['price']) * int(data['num_rooms']),
            'booking_date': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        db.bookings.insert_one(booking)
        flash('Hotel booking confirmed successfully!', 'success')
        return redirect(url_for('bookings'))  # ✅ corrected

    # GET request: pre-fill booking info from URL parameters
    hotel_info = {
        'hotel_name': request.args.get('hotel_name'),
        'location': request.args.get('location'),
        'checkin_date': request.args.get('checkin_date'),
        'checkout_date': request.args.get('checkout_date'),
        'num_rooms': int(request.args.get('num_rooms', 1)),
        'num_guests': int(request.args.get('num_guests', 1)),
        'price': int(request.args.get('price', 0)),
        'room_type': request.args.get('room_type', 'Deluxe')  # Optional: show default
    }

     # ✅ SNS for Hotel
    send_sns_notification(
        subject="Hotel Booking Confirmed",
        message=f"Hotel booking at {booking['name']} in {booking['location']} from {booking['checkin_date']} to {booking['checkout_date']} is confirmed.\nTotal: ₹{booking['total_price']}"
    )


    return render_template('confirm_hotel_details.html', hotel=hotel_info)

@app.route('/testimonials')
def testimonials():
    print("Testimonials route was triggered")
    return render_template('testimonials.html')


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

   
    
    