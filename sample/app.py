from flask import Flask, request, render_template, jsonify, redirect, url_for,flash,session
from supabase import create_client, Client
from werkzeug.security import generate_password_hash,check_password_hash
import config,os
import pytz
from datetime import datetime
import supabase
from dateutil.relativedelta import relativedelta  # For modifying timestamps by months
import traceback

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize Supabase client
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        coal_mine_name = request.form.get('coal_mine_name')
        type = request.form.get('type')
        location = request.form.get('location')
        contact = request.form.get('contact_number')
        mail = request.form.get('email')
        govt_registration = request.form.get('govt_registration')
        ownership = request.form.get('ownership')
        licence_number = request.form.get('licence_number')
        manager_name = request.form.get('manager_name')
        manager_contact = request.form.get('manager_contact')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Store data in Supabase
        user_data = {
            "coal_mine_name": coal_mine_name,
            "type": type,
            "location": location,
            "contact_number": contact,
            "email": mail,
            "govt_registration": govt_registration,
            "ownership": ownership,
            "licence_number": licence_number,
            "manager_name": manager_name,
            "manager_contact": manager_contact,
            "password": hashed_password
        }
        print(user_data)
        # Insert into the database
        response = supabase.table('coal_mines').insert(user_data).execute()
    
        if response.data :  # Success
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Please try again.', 'error')

    return render_template('register.html')

@app.route('/about')
def about():
    with open('static/about.txt', 'r') as file:
        about_content = file.read()
    return render_template('about.html', content=about_content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch the user from Supabase
        user = supabase.table('coal_mines').select('*').eq('email', email).execute()

        if user.data and len(user.data) > 0:
            # Validate password (assuming you hashed passwords during registration)
            hashed_password = user.data[0]['password']
            if check_password_hash(hashed_password, password):
                # Store user info in session and redirect to activity page
                session['email'] = user.data[0]['email']
                return redirect(url_for('profile'))
            else:
                print('Invalid password', 'error')
        else:
            print('User not found', 'error')

    return render_template('login.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/credits')
def credits():
    return render_template('credits.html')

@app.route('/activity', methods=['GET', 'POST'])
def activity():
    if request.method == 'POST':
        
        activity_type = request.form.get('activity_type')
        coal_mine_id = 4
        emissions = 0
      
        months_offset = 0
        people_count = request.form.get('people_count')

       
        if not people_count:
            return "People count cannot be empty", 400
        
        try:
            people_count = int(people_count)
        except ValueError:
            return "Invalid number for people count", 400
        try:
            
            if activity_type == 'excavation':
                coal_mined = float(request.form.get('coal_mined'))
                emission_factor = get_emission_factor(activity_type)
                emissions = coal_mined * emission_factor

            elif activity_type == 'transportation':
                vehicle_type = request.form.get('vehicle_type')
                fuel_type = request.form.get('fuel_type')
                distance_travelled=float(request.form.get('distance_travelled'))
                emission_factor = get_emission_factor(activity_type, f"{vehicle_type}_{fuel_type}".lower())
                
                emissions = distance_travelled * emission_factor

            elif activity_type == 'equipment':
                equipment_type = request.form.get('equipment_type')
                fuel_type = request.form.get('fuel_type')
                hours_used = float(request.form.get('hours_used'))
                fuel_consumption_rate=float(request.form.get('fuel_consumption_rate'))
                

                emission_factor = get_emission_factor(activity_type, f"{equipment_type}_{fuel_type}".lower())
                fuel_consumption=hours_used * fuel_consumption_rate
                emissions = fuel_consumption * emission_factor

            elif activity_type == 'blasting':  
                explosive_type = request.form.get('explosive_type')
                explosive_amount = float(request.form.get('explosive_amount'))
                emission_factor = get_emission_factor(activity_type, f"{explosive_type}".lower())
                emissions = explosive_amount * emission_factor

            
            activity_id = store_activity(coal_mine_id,activity_type, emissions, months_offset)

            
            response = supabase.table('activities').select('activity_type, emissions').eq('coal_mine_id', coal_mine_id).execute()
            activities = response.data
            
           
            activity_totals = {}
            for activity in activities:
                atype = activity['activity_type']
                activity_totals[atype] = activity_totals.get(atype, 0) + activity['emissions']

            
            activities_types = list(activity_totals.keys())
            emissions_values = list(activity_totals.values())

           
            total_emissions = sum(emissions_values)

            
            per_capita_emissions = total_emissions / people_count

            
            store_per_capita_emissions(coal_mine_id, total_emissions, per_capita_emissions, months_offset)
            print(total_emissions)
            print(per_capita_emissions)
           
            return redirect(url_for('result'))
           
        except Exception as e:
            error_details = traceback.format_exc()  
            print(f"Error calculating emissions: {error_details}")  
            return "An error occurred during emission calculation. Please try again.", 500 

    return render_template('activity.html')

@app.route('/result')
def result():
    try:
        coal_mine_id = 4 

     
        emissions_response = supabase.table('activities').select('activity_type, emissions').eq('coal_mine_id', coal_mine_id).execute()
        activities = emissions_response.data

        
        activity_totals = {}
        for activity in activities:
            atype = activity['activity_type']
            activity_totals[atype] = activity_totals.get(atype, 0) + activity['emissions']

       
        activity_types = list(activity_totals.keys())
        emissions_values = list(activity_totals.values())

      
        total_emissions = sum(emissions_values)

        
        per_capita_response = supabase.table('per_capita_emissions').select('per_capita_emissions').eq('coal_mine_id', coal_mine_id).order('created_at', desc=True).limit(1).execute()

        if per_capita_response.data:
            per_capita_emissions = per_capita_response.data[0]['per_capita_emissions']
        else:
            per_capita_emissions = 0  

            

       
        return render_template('result.html', 
                               activities_type=activity_types, 
                               emissions_values=emissions_values, 
                               total_emissions=total_emissions,
                               per_capita_emissions=per_capita_emissions)

    except Exception as e:
        error_details = traceback.format_exc()  
        print(f"Error displaying result: {error_details}")  
        return "An error occurred while displaying the result. Please try again.", 500


def get_emission_factor(activity_type, subtype=None):
    try:
      
        query = supabase.table('emission_factors').select('emission_factor').eq('activity_type', activity_type)
        if subtype:
            query = query.eq('subtype', subtype)
        response = query.execute()
        data = response.data

        if data:
            return data[0]['emission_factor']
        else:
            raise ValueError(f"No emission factor found for activity type: {activity_type}, subtype: {subtype}")

    except Exception as e:
        print(f"Error fetching emission factor: {e}")
        return 0  


def store_activity(coal_mine_id, activity_type, emissions, months_offset):
    try:
        
        current_time = datetime.now()
         
        print(current_time) 
        
        modified_time = current_time - relativedelta(months=months_offset)

        print(f"Date {months_offset} months ago: {modified_time.strftime('%Y-%m-%d')}")

        
        response = supabase.table('activities').insert({
            'coal_mine_id': coal_mine_id,
            'activity_type': activity_type,
            'emissions': emissions,'created_at': modified_time.isoformat() 
        }).execute()
        return response.data[0]['id']
    except Exception as e:
        print(f"Error storing activity: {e}")
        return None

def store_per_capita_emissions(coal_mine_id, total_emissions, per_capita_emissions, months_offset):
    try:
        
        current_time = datetime.now(pytz.UTC)
        
        
        modified_time = current_time - relativedelta(months=months_offset)
     
        response = supabase.table('per_capita_emissions').insert({
            'coal_mine_id': coal_mine_id,
            'total_emissions': total_emissions,
            'per_capita_emissions': per_capita_emissions,
            'created_at': modified_time.isoformat() 
        }).execute()
    except Exception as e:
        print(f"Error storing per capita emissions: {e}")

@app.route('/get_emissions_data', methods=['GET'])
def get_emissions_data():
    try:
        
        coal_mine_id = 4
        response = supabase.table('activities').select('*').eq('coal_mine_id', coal_mine_id).execute()
        data = response.data
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Error fetching emissions data: {e}"})


if __name__ == '__main__':
    app.run(debug=True)
