from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import mysql.connector as mysql
import requests  # Make sure to install requests if you haven't already

app = Flask(__name__)

# Generate a secure secret key for session management
app.secret_key = os.urandom(24)

# Function to create a database connection
def get_db_connection():
    try:
        return mysql.connect(
            host="localhost",
            user="root",
            password="fms-group3",
            database="pms"
        )
    except mysql.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# Route for displaying patients
@app.route('/')
def show_patients():
    fmsdb = get_db_connection()
    if fmsdb is None:
        return "Database connection failed", 500

    try:
        cursor = fmsdb.cursor(dictionary=True)

        # Query to fetch patients with their related services, medicines, and rooms
        query = """
            SELECT 
                p.patient_id, p.full_name, p.contact_number, p.insurance_info, p.billing_address, p.patient_type,
                s.service_name, s.quantity AS service_quantity, s.cost AS service_cost,
                m.medicine_name, m.quantity AS medicine_quantity, m.cost AS medicine_cost,
                r.room_number, r.bed_number, r.quantity AS room_quantity, r.cost AS room_cost
            FROM 
                patients p
            LEFT JOIN services s ON p.patient_id = s.patient_id
            LEFT JOIN medicines m ON p.patient_id = m.patient_id
            LEFT JOIN rooms r ON p.patient_id = r.patient_id
        """

        cursor.execute(query)
        patients = cursor.fetchall()

    except mysql.Error as err:
        print(f"Error during database query: {err}")  # Log specific error details
        return "Database query failed", 500
    finally:
        cursor.close()
        fmsdb.close()  # Close the database connection

    return render_template('patients.html', patients=patients)

@app.route('/send_to_fms/<int:patient_id>', methods=['POST'])
def send_to_fms(patient_id):
    fmsdb = get_db_connection()
    if fmsdb is None:
        return "Database connection failed", 500

    cursor = None
    try:
        cursor = fmsdb.cursor(dictionary=True)

        # Fetch patient data based on the patient_id
        patient_query = "SELECT * FROM patients WHERE patient_id = %s"
        cursor.execute(patient_query, (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for('show_patients'))

        # Prepare the data to send to FMS
        data_to_send = {
            'patient': {
                'patient_id': patient['patient_id'],
                'name': patient['full_name'],
                'contact_number': patient['contact_number'],
                'patient_type': patient['patient_type'],
                'billing_address': patient['billing_address'],
                'insurance_info': patient['insurance_info']
            },
            'services': [],
            'medicines': [],
            'rooms': []
        }

        # Fetch services, medicines, and rooms related to the patient
        services_query = "SELECT * FROM services WHERE patient_id = %s"
        cursor.execute(services_query, (patient_id,))
        data_to_send['services'] = cursor.fetchall()

        medicines_query = "SELECT * FROM medicines WHERE patient_id = %s"
        cursor.execute(medicines_query, (patient_id,))
        data_to_send['medicines'] = cursor.fetchall()

        rooms_query = "SELECT * FROM rooms WHERE patient_id = %s"
        cursor.execute(rooms_query, (patient_id,))
        data_to_send['rooms'] = cursor.fetchall()

        # Convert Decimal values to float for JSON serialization
        for service in data_to_send['services']:
            service['cost'] = float(service['cost'])  # Convert Decimal to float
            service['quantity'] = int(service['quantity'])  # Convert Decimal to int if necessary

        for medicine in data_to_send['medicines']:
            medicine['cost'] = float(medicine['cost'])  # Convert Decimal to float
            medicine['quantity'] = int(medicine['quantity'])  # Convert Decimal to int if necessary

        for room in data_to_send['rooms']:
            room['cost'] = float(room['cost'])  # Convert Decimal to float
            room['quantity'] = int(room['quantity'])  # Convert Decimal to int if necessary

        # Send data to FMS (example URL)
        response = requests.post('http://localhost:5000/hospital_patients', json=data_to_send)

        # Handle response from FMS
        if response.status_code == 200:
            flash("Data sent to FMS successfully!", "success")
        else:
            flash("Failed to send data to FMS.", "danger")

    except mysql.Error as err:
        print(f"Error during database query: {err}")
        return "Database query failed", 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for('show_patients'))
    finally:
        # Close the cursor if it was created
        if cursor:
            cursor.close()
        fmsdb.close()  # Close the database connection

    return redirect(url_for('show_patients'))

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=4000)
