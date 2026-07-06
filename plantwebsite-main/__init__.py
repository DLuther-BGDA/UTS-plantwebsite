# Import necessary Flask modules and other libraries
from flask import (
    Flask, g, render_template, request, session, url_for, jsonify, send_file,
    redirect, flash
)
import io
from flask_mail import Mail, Message
from extensions import bcrypt, db, init_app
import db_management
from User import User
import pandas as pd
import query
from datetime import datetime, date
import sys
import re

# Initialize the Flask application
app = Flask(__name__)
# Load configuration from a separate file
app.config.from_object("config.Config")

# Initialize Flask extensions
init_app(app)

# Import database models
from models import (
    ClientBusiness, DataSource, Family, LocalSpeciesInfo,
    Occurrence, Reserve, Species, SpeciesTraitJunction, Traits, Fauna
)

# Initialize Flask-Mail
mail = Mail(app)

# Function to send emails
def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config["MAIL_DEFAULT_SENDER"],
    )
    mail.send(msg)

# Global variables for data storage
df = None
species_list = []
# Dictionary defining groups of traits
trait_groups = {
    "Blossoming": ["flowering_cues", "flowering_time"],
    "Botany": ["bud_bank_location", "clonal_spread_mechanism", "flower_structural_sex_type", "genome_size", "ploidy", "root_system_type", "sex_type"],
    "Descriptive": ["flower_colour", "fruit_colour", "leaf_type", "parasitic", "plant_climbing_mechanism", "plant_growth_form", "plant_growth_substrate", "plant_height", "plant_physical_defence_structures"],
    "Fire recovery": ["fire_time_from_fire_to_50_percent_flowering", "fire_time_from_fire_to_50_percent_fruiting", "fire_time_from_fire_to_flowering", "fire_time_from_fire_to_flowering_decline", "fire_time_from_fire_to_fruiting", "fire_time_from_fire_to_peak_flowering"],
    "Fire response": ["life_history_ephemeral_class", "plant_tolerance_fire", "post_fire_flowering", "post_fire_recruitment", "resprouting_capacity", "resprouting_capacity_juvenile", "resprouting_capacity_proportion_individuals", "resprouting_capacity_time_from_germination"],
    "Germination": ["establishment_light_environment_index", "recruitment_time", "reproductive_light_environment_index", "root_structure", "seed_germination", "seed_germination_time", "seedling_establishment_conditions", "seedling_germination_location"],
    "Life history": ["life_history", "lifespan"],
    "Natural Growth": ["competitive_stratum", "dispersal_syndrome", "dispersers", "nitrogen_fixing", "resprouting_capacity_non_fire_disturbance", "sprout_depth", "stem_growth_habit", "storage_organ", "vegetative_reproduction_ability"],
    "Pollination": ["pollination_syndrome", "pollination_system"],
    "Seedbank": ["seedbank_location", "seedbank_longevity", "seedbank_longevity_class"],
    "Seeds": ["dispersal_unit", "fruiting_time", "reproductive_maturity", "seed_viability", "serotiny"],
    "Propagation": ["seed_dormancy_class", "seed_germination_treatment", "germination_treatment"],
    "Soil tolerances": ["plant_tolerance_calcicole", "plant_tolerance_salt", "plant_tolerance_soil_salinity", "plant_type_by_resource_use"],
    "Water response": ["plant_flood_regime_classification", "plant_tolerance_inundation", "plant_tolerance_snow", "plant_tolerance_water_logged_soils"]
}

# Function to load data from CSV
def load_data():
    global df, species_list
    if df is None:
        df = pd.read_csv("final Traits summary.csv")
        df = df.apply(lambda col: col.astype(str).str.split(" \\(").str[0].str.strip() if col.dtype == 'object' else col)
        species_list = sorted(df["species_name"].dropna().unique())
    return df

# Function to split trait values
def split_trait_values(val):
    if pd.isna(val):
        return []
    return [v.strip().lower() for v in re.split(r",| - |–| to | and |\+|-", str(val)) if v.strip()]

# Function to extract dropdown values for traits
def extract_dropdown_values(trait):
    load_data()
    values = df[trait].dropna().astype(str)
    dropdown_set = set()
    for val in values:
        split_vals = split_trait_values(val)
        dropdown_set.update(split_vals)
    return sorted(dropdown_set)

# Before each request, load trait data
@app.before_request
def before_request_load_trait_data():
    load_data()

# Route for the statistics page
@app.route('/statistics')
def statistics_page():
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    page = {'title': 'Statistics'}
    overall_stats = query.get_overall_statistics(db.session)

    return render_template('statistics.html',
                           username=session["username"],
                           is_admin=session["is_admin"],
                           page=page,
                           stats=overall_stats)

# Route to view traits of selected species
@app.route("/view_traits", methods=["GET", "POST"])
def view_traits():
    selected_species = []
    species_data = {}
    if request.method == "POST":
        selected_species = request.form.getlist("selected_species")
        if selected_species:
            for species in selected_species:
                row = df[df["species_name"] == species].iloc[0]
                species_traits = {}
                for group_name, traits in trait_groups.items():
                    group_data = {trait: row[trait] for trait in traits if trait in row and pd.notna(row[trait])}
                    if group_data:
                        species_traits[group_name] = group_data
                species_data[species] = species_traits
    return render_template("view_traits.html", species_list=species_list, selected_species=selected_species, species_data=species_data)

# Route to find flowers based on trait filters
@app.route("/find_flowers", methods=["GET", "POST"])
def find_flowers():
    matching_species = []
    selected_groups = []
    selected_traits = []
    filters_display = {}

    if request.method == "POST":
        selected_groups = request.form.getlist("selected_groups")
        available_traits = []
        for group in selected_groups:
            available_traits.extend([trait for trait in trait_groups[group] if trait in df.columns])

        selected_traits = request.form.getlist("selected_traits")
        filters = {}
        for trait in selected_traits:
            raw_selected_vals = request.form.getlist(f"values_for_{trait}")
            selected_vals_processed = []
            for val in raw_selected_vals:
                selected_vals_processed.extend(split_trait_values(val.lower()))
            if selected_vals_processed:
                filters[trait] = list(set(selected_vals_processed))
                filters_display[trait] = raw_selected_vals

        if filters:
            filtered_df = df.copy()
            for trait, vals in filters.items():
                def match_any(val):
                    val_list = split_trait_values(val)
                    return any(v in val_list for v in vals)
                if trait in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df[trait].apply(lambda x: match_any(x) if pd.notna(x) else False)]

            if not filtered_df.empty:
                matching_species = filtered_df[["species_name"] + list(filters.keys())].to_dict(orient='records')
        else:
            matching_species = []

    all_trait_groups = list(trait_groups.keys())
    available_traits_for_display = [trait for group in selected_groups for trait in trait_groups[group] if trait in df.columns]

    trait_value_options = {trait: extract_dropdown_values(trait) for trait in selected_traits}

    return render_template(
        "find_flowers.html",
        all_trait_groups=all_trait_groups,
        selected_groups=selected_groups,
        available_traits_for_display=available_traits_for_display,
        selected_traits=selected_traits,
        trait_value_options=trait_value_options,
        filters_display=filters_display,
        matching_species=matching_species
    )

# Route to compare traits of multiple species
@app.route("/compare_traits", methods=["GET", "POST"])
def compare_traits():
    selected_species = []
    compare_data = None
    if request.method == "POST":
        selected_species = request.form.getlist("selected_species")
        if selected_species:
            compare_df = df[df["species_name"].isin(selected_species)].set_index("species_name")
            compare_data = compare_df.to_dict(orient='index')
    return render_template("compare_traits.html", species_list=species_list, selected_species=selected_species, compare_data=compare_data)

# Route for data update page (redirects to under construction)
@app.route('/update_data')
def update_page():
    return redirect(url_for('under_construction_page'))

# Route for the map page
@app.route('/map')
def map_page():
    return render_template('map.html')

# Route for the home page
@app.route('/home')
def home_page():
    return render_template('home.html')

# Route for the under construction page
@app.route('/under_construction')
def under_construction_page():
    return render_template('under_construction.html')

# Route for the about page (redirects to external link)
@app.route('/about')
def about_page():
    about_site_link = "https://docs.google.com/document/d/1lbjMmRwctoKtE66DqXltRtMc_ayN5u1vQrCWArIDzvc/edit?usp=sharing"
    return redirect(about_site_link)

# Route for the user guide page (redirects to external link)
@app.route('/user_guide')
def user_guide_page():
    user_guide_link = "https://drive.google.com/file/d/1YwgmjvTLvRYptbGJi_3JOybTsq-qaW0C/view?usp=sharing"
    return redirect(user_guide_link)

# Route for the fire experiment page (redirects to under construction)
@app.route('/fire_experiment')
def fire_experiment_page():
    return redirect(url_for('under_construction_page'))

# Route for the feedback page (redirects to external link)
@app.route('/feedback')
def feedback_page():
    feedback_link = "https://docs.google.com/document/d/1qPcz25Z4GaDAbtcOG6YVc1SyVVutNPCy/edit?usp=sharing&ouid=102170301768105281260&rtpof=true&sd=true"
    return redirect(feedback_link)

# API endpoint to get map filter options
@app.route('/api/map_filters')
def get_map_filters():
    filter_options = query.get_options_occurrences(db.session)

    year_options_from_db = filter_options['yearOptions']
    full_year_range = []
    if year_options_from_db:
        min_year = min(year_options_from_db)
        max_year = max(year_options_from_db)
        full_year_range = list(range(min_year, max_year + 1))

    return jsonify({
        "species": filter_options['speciesOptions'],
        "datasets": filter_options['datasetOptions'],
        "reserves": filter_options['reserveOptions'],
        "planted_natives": filter_options['plantedNativeOptions'],
        "years": full_year_range,
        "threatened_statuses": filter_options['threatenedStatusOptions']
    })

# API endpoint to get map data based on filters
@app.route('/api/map_data')
def get_map_data():
    species = request.args.get('species')
    dataset = request.args.get('dataset')
    reserve = request.args.get('reserve')
    planted_native = request.args.get('planted_native')
    start_year = request.args.get('start_year')
    end_year = request.args.get('end_year')
    threatened_status = request.args.get('rare')

    try:
        observations = query.get_observations(
            db_session=db.session,
            species=species,
            dataset=dataset,
            reserve=reserve,
            planted_native=planted_native,
            start_year=start_year,
            end_year=end_year,
            rare=threatened_status
        )
        return jsonify(observations)
    except Exception as e:
        print(f"Error fetching map data: {e}", file=sys.stderr)
        return jsonify({"error": "Failed to fetch map data", "details": str(e)}), 500

# Default route for the application
@app.route("/")
def index():
    session['edit_mode'] = False
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))
    return redirect(url_for("flora_dashboard"))

# Route to view detailed trait information
@app.route('/traits', methods=['GET', 'POST'])
def traits_viewer():
    try:
        traits_df = pd.read_excel('TraitsCombine-helen-Dorothy.xlsx', sheet_name=0)
        values_df = pd.read_excel('Value.xlsx')
    except FileNotFoundError as e:
        print(f"ERROR: Excel file not found. Ensure 'TraitsCombine-helen-Dorothy.xlsx' and 'Value.xlsx' are in the /app directory of the container. Details: {e}", file=sys.stderr)
        return "Internal Server Error: Required data files not found.", 500

    trait_list = sorted(traits_df['trait'].unique())
    selected_trait = request.form.get('trait_select') if request.method == 'POST' else None

    trait_info = None
    value_table = None

    if selected_trait:
        trait_info = traits_df[traits_df['trait'] == selected_trait].to_dict(orient='records')[0]
        value_table = values_df[values_df['trait'] == selected_trait][[
            'allowed_values_levels', 'categorical_trait_description'
        ]].rename(columns={
            'allowed_values_levels': 'Value',
            'categorical_trait_description': 'Description'
        }).to_dict(orient='records')

    return render_template(
        'traits.html',
        trait_list=trait_list,
        selected_trait=selected_trait,
        trait_info=trait_info,
        value_table=value_table
    )

# Route for forgot password functionality
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    session['edit_mode'] = False
    if (request.method == "POST"):
        email = request.form["email"]
        user = db.session.query(User).filter_by(email=email).one_or_none()
        if user is None:
            return render_template("forgot-password.html", msg="""Invalid email address.""")

        if user.password is None or user.password == '':
            return render_template("forgot-password.html", msg="""This account has not yet set a password.
                                   Please use the 'Register New Account' option first.""")

        token = user.generate_token(app, email)
        reset_url = url_for("reset_password", token=token, _external=True)
        html = render_template("reset_password_email.html", reset_url=reset_url)
        subject = "Reset your password"
        send_email(user.email, subject, html)
        return render_template("login.html", msg="""Password reset link
                               has been sent to your email address.""")
    else:
        page = {'title': 'Forgot Password'}
        return render_template('forgot-password.html', page=page)

# Route to reset password using a token
@app.route("/reset_password/<token>", methods = ['POST', 'GET'])
def reset_password(token):
    session['edit_mode'] = False

    email = User.confirm_token(app, token)
    user = db.session.query(User).filter_by(email=email).one_or_none()
    if not email or not user:
        return render_template("login.html", msg="""The password reset
                               link is invalid or has expired.""")

    if request.method == 'POST':
        password = request.form["password"]
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return render_template("login.html", msg="""Password has been reset.""")
    else:
        return render_template('reset_password.html')

# Route for user login
@app.route('/login', methods = ['POST', 'GET'])
def login():
    session['edit_mode'] = False
    page = {'title' : 'login'}
    if (request.method == 'POST'):
        email = request.form["username"]
        password = request.form["password"]
        user = db.session.query(User).filter_by(email=email).one_or_none()

        if user is None:
            return render_template('login.html', msg = """Username or password is incorrect.""")

        if user.password is None or user.password == '':
            return render_template('login.html', msg = """Your account requires initial setup. Please use the 'Register New Account' button.""")

        if user.verify_password(password) == False:
            return render_template('login.html', msg = """Username or password is incorrect.""")

        session['logged_in'] = True
        session['username'] = email
        session['is_admin'] = user.is_admin()
        return redirect(url_for('home_page'))

    else:
        if ('logged_in' in session and session['logged_in'] == True):
            return redirect(url_for('index'))
        return render_template('login.html', page = page)

# Route for user settings
@app.route('/settings')
def settings():
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))
    session['edit_mode'] = False
    return render_template('settings.html', username = session["username"], is_admin = session["is_admin"])

# Route for new user registration (sign-up)
@app.route('/signup', methods = ['POST', 'GET'])
def sign_up():
    if ('logged_in' in session and session['logged_in'] == True):
        return redirect(url_for('index'))

    session['edit_mode'] = False
    page = {'title' : 'Register New Account'}
    error_msg = ""

    if (request.method == 'POST'):
        username = request.form['username']
        secret_password_attempt = request.form['secret_password'].lower()
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']

        user = db.session.query(User).filter_by(email=username).one_or_none()

        if user is None:
            error_msg = "Account not found for initial setup. Please check your email."
        elif user.password is not None and user.password != '':
            error_msg = "This account has already been set up. Please use the login page."
        elif secret_password_attempt != app.config['SECRET_INITIAL_PASSWORD']:
            error_msg = "Incorrect secret password."
        elif new_password != confirm_new_password:
            error_msg = "New passwords do not match."
        else:
            user.set_password(new_password)
            db.session.add(user)
            db.session.commit()
            return render_template("login.html", msg="""Your account has been successfully set up. You can now log in with your new password.""")

    return render_template('signup.html', page = page, error_msg = error_msg)

# Route to manage users
@app.route('/manage_users', methods=['GET'])
def manage_users():
    # Check if user is logged in
    if 'logged_in' not in session or not session['logged_in']:
        flash("Please log in to access this page.")
        return redirect(url_for('login'))
    # Check if user is an administrator
    if not session.get('is_admin'):
        flash("You do not have administrative privileges to access this page.", "error")
        return redirect(url_for('home_page'))

    # Get all users from the database
    all_users = db.session.query(User).all()

    # Render the manage users page
    return render_template('manage_users.html',
                           username=session["username"],
                           is_admin=session["is_admin"],
                           users=all_users)

# Route to create a new user
@app.route('/create_user', methods=['POST'])
def create_user():
    # Check if user is logged in
    if 'logged_in' not in session or not session['logged_in']:
        flash("Please log in to perform this action.")
        return redirect(url_for('login'))
    # Check if user is an administrator
    if not session.get('is_admin'):
        flash("You do not have administrative privileges to perform this action.", "error")
        return redirect(url_for('home_page'))

    # Get email from form data
    email = request.form.get('email')

    # Validate email input
    if not email:
        flash("Email address is required to create a user.", "error")
        return redirect(url_for('manage_users'))

    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email format.", "error")
        return redirect(url_for('manage_users'))

    # Check if user already exists
    existing_user = db.session.query(User).filter_by(email=email).one_or_none()
    if existing_user:
        flash(f"User with email '{email}' already exists.", "error")
    else:
        try:
            # Create new user and add to database
            new_user = User(email=email, password=None, write_permission=False, role='user')
            db.session.add(new_user)
            db.session.commit()
            flash(f"User '{email}' created successfully. They can now set their password via 'Register New Account'.", "success")
        except Exception as e:
            # Rollback on error
            db.session.rollback()
            flash(f"Error creating user: {e}", "error")
            print(f"Error creating user: {e}", file=sys.stderr)

    # Redirect back to manage users page
    return redirect(url_for('manage_users'))

# Route to toggle user role (admin/regular user)
@app.route('/toggle_user_role/<int:user_id>', methods=['POST'])
def toggle_user_role(user_id):
    # Check if user is logged in
    if 'logged_in' not in session or not session['logged_in']:
        flash("Please log in to perform this action.")
        return redirect(url_for('login'))
    # Check if user is an administrator
    if not session.get('is_admin'):
        flash("You do not have administrative privileges to perform this action.", "error")
        return redirect(url_for('home_page'))

    # Get the user to toggle by ID
    user_to_toggle = db.session.query(User).get(user_id)

    if user_to_toggle:
        try:
            # Prevent demoting own admin account
            current_user_email = session.get("username")
            if user_to_toggle.email == current_user_email and user_to_toggle.role == 'Administrator':
                flash("Cannot demote your own administrator account.", "error")
            else:
                # Toggle the user's role
                if user_to_toggle.role == 'user':
                    user_to_toggle.role = 'Administrator'
                    flash(f"User '{user_to_toggle.email}' is now an Administrator.", "success")
                else:
                    user_to_toggle.role = 'user'
                    flash(f"User '{user_to_toggle.email}' is now a regular user.", "success")
                db.session.add(user_to_toggle)
                db.session.commit()
        except Exception as e:
            # Rollback on error
            db.session.rollback()
            flash(f"Error toggling role for user '{user_to_toggle.email}': {e}", "error")
            print(f"Error toggling role: {e}", file=sys.stderr)
    else:
        flash(f"User with ID {user_id} not found.", "error")

    # Redirect back to manage users page
    return redirect(url_for('manage_users'))

# Route to delete a user
@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    # Check if user is logged in
    if 'logged_in' not in session or not session['logged_in']:
        flash("Please log in to perform this action.")
        return redirect(url_for('login'))
    # Check if user is an administrator
    if not session.get('is_admin'):
        flash("You do not have administrative privileges to perform this action.", "error")
        return redirect(url_for('home_page'))

    # Get the user to delete by ID
    user_to_delete = db.session.query(User).get(user_id)

    if user_to_delete:
        try:
            # Prevent deleting own account
            current_user_email = session.get("username")
            if user_to_delete.email == current_user_email:
                flash("Cannot delete your own account.", "error")
            else:
                # Delete the user from the database
                db.session.delete(user_to_delete)
                db.session.commit()
                flash(f"User '{user_to_delete.email}' deleted successfully.", "success")
        except Exception as e:
            # Rollback on error
            db.session.rollback()
            flash(f"Error deleting user '{user_to_delete.email}': {e}", "error")
            print(f"Error deleting user: {e}", file=sys.stderr)
    else:
        flash(f"User with ID {user_id} not found.", "error")

    # Redirect back to manage users page
    return redirect(url_for('manage_users'))

# Route for the flora dashboard
@app.route('/flora_dashboard', methods = ['GET', 'POST'])
def flora_dashboard():
    # Check if user is logged in
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    # Set page title and get filter options
    page = {'title' : 'Flora Dashboard'}
    filterOptions = query.get_options_occurrences(db.session)

    # Get pagination parameters
    page_num = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Get filter parameters from request arguments
    species_param = request.args.get('species')
    dataset_param = request.args.get('dataset')
    reserve_param = request.args.get('reserve')
    locality_param = request.args.get('locality')
    habitat_param = request.args.get('habitat')
    basis_of_record_param = request.args.get('basis')
    native_param = request.args.get('native')
    rare_param = request.args.get('rare')

    start_year_param = request.args.get('start_year')
    end_year_param = request.args.get('end_year')

    selected_reserves_param = request.args.get('selected_reserves_input')
    selected_reserves_list = selected_reserves_param.split(',') if selected_reserves_param else []

    # Determine effective reserve filter
    effective_reserve_filter = selected_reserves_list if selected_reserves_list else (reserve_param.split(',') if reserve_param else None)

    # Get paginated data
    paginated_data_query = query.get_observations_query(
        db.session,
        species=species_param,
        dataset=dataset_param,
        reserve=effective_reserve_filter,
        locality=locality_param,
        habitat=habitat_param,
        basis_of_record=basis_of_record_param,
        planted_native=native_param,
        rare=rare_param,

        start_year=start_year_param,
        end_year=end_year_param
    )

    paginated_results = paginated_data_query.paginate(page=page_num, per_page=per_page, error_out=False)
    result = [obs.to_dict() for obs in paginated_results.items]
    total_results = paginated_results.total

    # Get full filtered data for download/export
    full_filtered_data_query = query.get_observations_query(
        db.session,
        species=species_param,
        dataset=dataset_param,
        reserve=effective_reserve_filter,
        locality=locality_param,
        habitat=habitat_param,
        basis_of_record=basis_of_record_param,
        planted_native=native_param,
        rare=rare_param,

        start_year=start_year_param,
        end_year=end_year_param
    )

    full_filtered_result = [obs.to_dict() for obs in full_filtered_data_query.all()]

    # Determine which template to render based on edit mode
    template_name = 'editable_dashboard.html' if session.get('edit_mode') else 'flora_dashboard.html'

    # Render the flora dashboard template
    return render_template(template_name,
                           username=session["username"],
                           is_admin=session["is_admin"],
                           page=page,
                           speciesOptions=filterOptions["speciesOptions"],
                           datasetOptions=filterOptions["datasetOptions"],
                           localityOptions=filterOptions["localityOptions"],
                           habitatOptions=filterOptions["habitatOptions"],
                           basisOptions=filterOptions["basisOptions"],
                           reserveOptions=filterOptions["reserveOptions"],
                           filtered_result=result,
                           full_filtered_result=full_filtered_result,
                           species=species_param or '',
                           dataset=dataset_param or '',
                           locality=locality_param or '',
                           habitat=habitat_param or '',
                           basis=basis_of_record_param or '',
                           reserve='',
                           selected_reserves=selected_reserves_list,
                           native=native_param or '',
                           rare=rare_param or '',
                           start_year=start_year_param or '',
                           end_year=end_year_param or '',
                           is_flora=True,
                           page_num=page_num,
                           per_page=per_page,
                           total_results=total_results,
                           has_next=paginated_results.has_next,
                           has_prev=paginated_results.prev_num,
                           next_num=paginated_results.next_num,
                           prev_num=paginated_results.prev_num
                           )

# Route to filter flora data
@app.route('/filter_flora', methods = ['POST', 'GET'])
def filter_flora():
    # Check if user is logged in
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    # Get form data
    form_data = request.form.to_dict()

    # Get selected reserves from form
    selected_reserves_input = request.form.getlist('selected_reserves')

    # Convert selected reserves to a comma-separated string
    if selected_reserves_input:
        selected_reserves_str = ','.join(selected_reserves_input)
    else:
        selected_reserves_str = ''

    # Prepare arguments for redirect
    redirect_args = {
        'species': form_data.get('species', ''),
        'dataset': form_data.get('dataset', ''),
        'reserve': form_data.get('reserve', ''),
        'locality': form_data.get('locality', ''),
        'habitat': form_data.get('habitat', ''),
        'basis': form_data.get('basis', ''),
        'native': form_data.get('native', ''),
        'rare': form_data.get('rare', ''),
        'start_year': form_data.get('start_year', ''),
        'end_year': form_data.get('end_year', ''),
        'selected_reserves_input': selected_reserves_str,
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 20, type=int)
    }

    # Redirect to flora dashboard with filter arguments
    return redirect(url_for('flora_dashboard', **redirect_args))

# Route for the fauna dashboard
@app.route('/fauna_dashboard', methods = ['GET', 'POST'])
def fauna_dashboard():
    # Check if user is logged in
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    # Set page title
    page = {'title' : 'Fauna Dashboard'}

    # Helper function to clean parameters
    def clean_param(param):
        return param.strip() if param and str(param).strip() else None

    # Get filter options for fauna
    filterOptions = query.get_options_fauna(db.session)

    # Get pagination parameters
    page_num = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Get filter parameters from request arguments and clean them
    genus_param = clean_param(request.args.get('genus'))
    species_param = clean_param(request.args.get('species'))
    family_param = clean_param(request.args.get('family'))
    vernacular_name_param = clean_param(request.args.get('vernacular_name'))
    class_name_param = clean_param(request.args.get('class_name'))
    rare_endangered_param = clean_param(request.args.get('rare_endangered'))
    local_rare_endangered_param = clean_param(request.args.get('local_rare_endangered'))
    exotic_param = clean_param(request.args.get('exotic'))
    year_param = clean_param(request.args.get('year'))
    reserve_name_param = clean_param(request.args.get('reserve_name'))

    # Debug print statement for parameters
    print(f"DEBUG: Params to query in fauna_dashboard: genus={repr(genus_param)}, species={repr(species_param)}, class_name={repr(class_name_param)}, year={repr(year_param)}, reserve_name={repr(reserve_name_param)}")

    # Get paginated fauna data
    paginated_data_query = query.get_fauna_query(
        db.session,
        genus=genus_param,
        species=species_param,
        family=family_param,
        vernacular_name=vernacular_name_param,
        class_name=class_name_param,
        rare_endangered=rare_endangered_param,
        local_rare_endangered=local_rare_endangered_param,
        exotic=exotic_param,
        year=year_param,
        reserve_name=reserve_name_param
    )

    paginated_results = paginated_data_query.paginate(page=page_num, per_page=per_page, error_out=False)

    # Process paginated results
    result = []
    for fauna_obj in paginated_results.items:
        fauna_dict = fauna_obj.to_dict()
        fauna_dict.pop('old_location_name', None)
        fauna_dict.pop('fauna_id', None)
        result.append(fauna_dict)

    total_results = paginated_results.total

    # Get full filtered fauna data for download/export
    full_filtered_fauna_query = query.get_fauna_query(
        db.session,
        genus=genus_param,
        species=species_param,
        family=family_param,
        vernacular_name=vernacular_name_param,
        class_name=class_name_param,
        rare_endangered=rare_endangered_param,
        local_rare_endangered=local_rare_endangered_param,
        exotic=exotic_param,
        year=year_param,
        reserve_name=reserve_name_param
    )

    full_filtered_fauna_result = []
    for fauna_obj in full_filtered_fauna_query.all():
        fauna_dict = fauna_obj.to_dict()
        fauna_dict.pop('old_location_name', None)
        fauna_dict.pop('fauna_id', None)
        full_filtered_fauna_result.append(fauna_dict)

    # Set template name
    template_name = 'fauna_dashboard.html'

    # Render the fauna dashboard template
    return render_template(template_name,
                           username=session["username"],
                           is_admin=session["is_admin"],
                           page=page,
                           genusOptions=filterOptions["genusOptions"],
                           speciesOptions=filterOptions["speciesOptions"],
                           familyOptions=filterOptions["familyOptions"],
                           vernacularNameOptions=filterOptions["vernacularNameOptions"],
                           classNameOptions=filterOptions["classNameOptions"],
                           rareEndangeredOptions=filterOptions["rareEndangeredOptions"],
                           localRareEndangeredOptions=filterOptions["localRareEndangeredOptions"],
                           exoticOptions=filterOptions["exoticOptions"],
                           yearOptions=filterOptions["yearOptions"],
                           reserveNameOptions=filterOptions["reserveNameOptions"],
                           filtered_result=result,
                           full_filtered_fauna_result=full_filtered_fauna_result,

                           genus=genus_param or '',
                           species=species_param or '',
                           family=family_param or '',
                           vernacular_name=vernacular_name_param or '',
                           class_name=class_name_param or '',
                           rare_endangered=rare_endangered_param or '',
                           local_rare_endangered=local_rare_endangered_param or '',
                           exotic=exotic_param or '',
                           year=year_param or '',
                           reserve_name=reserve_name_param or '',
                           is_flora=False,
                           page_num=page_num,
                           per_page=per_page,
                           total_results=total_results,
                           has_next=paginated_results.has_next,
                           has_prev=paginated_results.prev_num,
                           next_num=paginated_results.next_num,
                           prev_num=paginated_results.prev_num
                           )

# Route to filter fauna data
@app.route('/filter_fauna', methods = ['POST', 'GET'])
def filter_fauna():
    # Check if user is logged in
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    # Get form data
    form_data = request.form.to_dict()

    # Prepare arguments for redirect
    redirect_args = {
        'genus': form_data.get('genus', ''),
        'species': form_data.get('species', ''),
        'family': form_data.get('family', ''),
        'vernacular_name': form_data.get('vernacular_name', ''),
        'class_name': form_data.get('class_name', ''),
        'rare_endangered': form_data.get('rare_endangered', ''),
        'local_rare_endangered': form_data.get('local_rare_endangered', ''),
        'exotic': form_data.get('exotic', ''),
        'year': form_data.get('year', ''),
        'reserve_name': form_data.get('reserve_name', ''),
        'page': request.args.get('page', 1, type=int),
        'per_page': request.args.get('per_page', 20, type=int)
    }

    # Redirect to fauna dashboard with filter arguments
    return redirect(url_for('fauna_dashboard', **redirect_args))

# Route to save flora table data
@app.route('/save_table_flora', methods = ['POST'])
def save_table_flora():
    # Get data from the JSON request
    data = request.json
    original_data = data['originalData']
    new_data = data['newData']
    replace_all = data['replaceAll']

    # SQL query to update a single occurrence record
    query_str_1 = """
    UPDATE Occurrence
    SET scientificName = :scientificName, eventDate = :eventDate, datasetName = :datasetName,
        reserveName = :reserveName, decimalLatitude = :decimalLatitude, decimalLongitude = :decimalLongitude,
        individualCount = :individualCount, reproductiveCondition = :reproductiveCondition,
        establishmentMeans = :establishmentMeans, occurrenceRemarks = :occurrenceRemarks,
        year = :year, month = :month, day = :day, habitat = :habitat,
        samplingProtocol = :samplingProtocol, locality = :locality, locationRemarks = :locationRemarks,
        identifiedBy = :identifiedBy, dateIdentified = :dateIdentified,
        ownerInstitutionCode = :ownerInstitutionCode, basisOfRecord = :basisOfRecord,
        dataGeneralizations = :dataGeneralizations, recordedBy = :recordedBy,
        clientBusinessName = :clientBusinessName
    WHERE occurrenceId = :occurrenceId
    """
    try:
        # Parameters for the first update query
        params_1 = {
            'scientificName': new_data.get('scientificName'),
            'eventDate': new_data.get('eventDate'),
            'datasetName': new_data.get('datasetName'),
            'reserveName': new_data.get('reserveName'),
            'decimalLatitude': new_data.get('decimalLatitude'),
            'decimalLongitude': new_data.get('decimalLongitude'),
            'individualCount': new_data.get('individualCount'),
            'reproductiveCondition': new_data.get('reproductiveCondition'),
            'establishmentMeans': new_data.get('establishmentMeans'),
            'occurrenceRemarks': new_data.get('occurrenceRemarks'),
            'year': new_data.get('year'),
            'month': new_data.get('month'),
            'day': new_data.get('day'),
            'habitat': new_data.get('habitat'),
            'samplingProtocol': new_data.get('samplingProtocol'),
            'locality': new_data.get('locality'),
            'locationRemarks': new_data.get('locationRemarks'),
            'identifiedBy': new_data.get('identifiedBy'),
            'dateIdentified': new_data.get('dateIdentified'),
            'ownerInstitutionCode': new_data.get('ownerInstitutionCode'),
            'basisOfRecord': new_data.get('basisOfRecord'),
            'dataGeneralizations': new_data.get('dataGeneralizations'),
            'recordedBy': new_data.get('recordedBy'),
            'clientBusinessName': new_data.get('clientBusinessName'),
            'occurrenceId': original_data['occurrenceId']
        }

        # Execute the first update
        db_management.update_db(db, query_str_1, params_1)

        # If 'replace_all' is true, perform a bulk update
        if replace_all:
            set_str_ls = []
            where_str_ls = ["scientificName = :original_scientificName"]
            params_2 = {'original_scientificName': original_data['scientificName']}

            for column in replace_all:
                # Map display column names to database column names
                db_column = {
                    'Scientific Name': 'scientificName',
                    'Event Date': 'eventDate',
                    'Dataset Name': 'datasetName',
                    'Reserve Name': 'reserveName',
                    'Decimal Latitude': 'decimalLatitude',
                    'Decimal Longitude': 'decimalLongitude',
                    'Individual Count': 'individualCount',
                    'Reproductive Condition': 'reproductiveCondition',
                    'Establishment Means': 'establishmentMeans',
                    'Occurrence Remarks': 'occurrenceRemarks',
                    'Year': 'year',
                    'Month': 'month',
                    'Day': 'day',
                    'Habitat': 'habitat',
                    'Sampling Protocol': 'samplingProtocol',
                    'Locality': 'locality',
                    'Location Remarks': 'locationRemarks',
                    'Identified By': 'identifiedBy',
                    'Date Identified': 'dateIdentified',
                    'Owner Institution Code': 'ownerInstitutionCode',
                    'Basis of Record': 'basisOfRecord',
                    'Data Generalizations': 'dataGeneralizations',
                    'Recorded By': 'recordedBy',
                    'Client Business Name': 'clientBusinessName'
                }.get(column, column)

                set_str_ls.append(f'"{db_column}" = :new_{db_column}')
                params_2[f'new_{db_column}'] = new_data.get(column)

                if db_column != 'scientificName':
                    where_str_ls.append(f'"{db_column}" = :original_{db_column}')
                    params_2[f'original_{db_column}'] = original_data.get(column)

            # Construct and execute the second update query
            query_str_2 = 'UPDATE Occurrence SET ' + ', '.join(set_str_ls) + ' WHERE ' + ' AND '.join(where_str_ls)

            db_management.update_db(db, query_str_2, params_2)

        # Return success message
        return jsonify({"message": "Update successful"}), 200
    except Exception as e:
        # Handle errors during update
        print(f"Exception occurred in save_table_flora: {type(e).__name__}, {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

# Route to generate reports
@app.route('/report', methods=['GET', 'POST'])
def generate_report():
    # Check if user is logged in
    if ('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    # Get report type and name from form or set defaults
    report_type = request.form.get('report_type', "Flora")
    report_name = request.form.get('report_name', "All Species")

    result = []

    # Debug print statements
    print(f"DEBUG: Request Method: {request.method}")
    print(f"DEBUG: Form Data: {request.form}")
    print(f"DEBUG: Initial Report Type: {report_type}, Report Name: {report_name}")

    if request.method == 'POST':
        print(f"DEBUG: Processing POST - Report Type={report_type}, Name={report_name}")

        # Handle Flora reports
        if report_type == "Flora":
            if report_name == "All Species":
                result = query.get_flora_all_species_report(db.session)
            elif report_name == "Summary Report":
                result = query.get_summary_report(db.session, "Flora")
            elif report_name == "Report by Reserve":
                result = query.get_flora_report_by_reserve(db.session)
            elif report_name == "Native Flora = 1 Site":
                try:
                    result = query.get_native_flora_equal_1_1_site(db.session)
                except AttributeError:
                    flash("Native Flora = 1 Site report is not implemented or has issues.", "error")
                    result = []
            else:
                flash("Invalid Flora report type selected.", "error")

        # Handle Fauna reports
        elif report_type == "Fauna":
            if report_name == "All Species":
                result = query.get_fauna_all_species_report(db.session)
            elif report_name == "Summary Report":
                result = query.get_summary_report(db.session, "Fauna")
            else:
                flash("Invalid Fauna report type selected.", "error")
        else:
            flash("Invalid report type selected.", "error")

        # Display warning if no results found
        if not result:
            print(f"DEBUG: No results found for report Type={report_type}, Name={report_name}")
            flash(f"No data available for '{report_name}' for {report_type}.", "warning")

    # Initial GET request for default report
    if not result and request.method == 'GET':
        report_type = "Flora"
        report_name = "All Species"
        result = query.get_flora_all_species_report(db.session)
        print(f"DEBUG: Initial GET load - Report Type={report_type}, Name={report_name}, Result Count: {len(result)}")

    # Render the report page
    return render_template('report.html',
                           username = session["username"],
                           is_admin = session["is_admin"],
                           result=result,
                           report=report_name,
                           report_type=report_type,
                           is_flora=(report_type == "Flora"))

# Route to download reports
@app.route('/download', methods=['POST'])
def download_report():
    # Get report type and name from form
    report_type = request.form.get('report_type')
    report_name = request.form.get('report_name')
    print("Report Type:", report_type)
    print("Report Name:", report_name)

    # Validate report type and name
    if not report_type or not report_name:
        flash("Missing report_type or report_name for download.", "error")
        return redirect(url_for('generate_report'))

    result = None

    # Retrieve data based on report type and name
    if report_type == "Flora":
        if report_name == "All Species":
            result = query.get_flora_all_species_report(db.session)
        elif report_name == "Summary Report":
            result = query.get_summary_report(db.session, "Flora")
        elif report_name == "Report by Reserve":
            result = query.get_flora_report_by_reserve(db.session)
        elif report_name == "Native Flora = 1 Site":
            try:
                result = query.get_native_flora_equal_1_site(db.session)
            except AttributeError:
                flash("Native Flora = 1 Site report is not implemented or has issues, cannot download.", "error")
                return redirect(url_for('generate_report'))
        else:
            flash("Invalid Flora report type for download.", "error")
            return redirect(url_for('generate_report'))

    elif report_type == "Fauna":
        if report_name == "All Species":
            result = query.get_fauna_all_species_report(db.session)
        elif report_name == "Summary Report":
            result = query.get_summary_report(db.session, "Fauna")
        else:
            flash("Invalid Fauna report type for download.", "error")
            return redirect(url_for('generate_report'))
    else:
        flash("Invalid report type for download.", "error")
        return redirect(url_for('generate_report'))

    # If no data, display warning
    if not result:
        flash(f"No data to download for '{report_name}' for {report_type}.", "warning")
        return redirect(url_for('generate_report'))

    try:
        # Create a Pandas DataFrame from the result
        df_to_download = pd.DataFrame(result)
    except Exception as e:
        flash(f"Error creating DataFrame for download: {e}", "error")
        print(f"Error creating DataFrame for download: {e}", file=sys.stderr)
        return redirect(url_for('generate_report'))

    # Create an in-memory Excel file
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df_to_download.to_excel(writer, index=False, sheet_name='Report')
    writer.close()
    output.seek(0)

    # Send the Excel file as an attachment
    return send_file(output, as_attachment=True, download_name=f'{report_type}_{report_name}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Route to log out a user
@app.route('/logout')
def logout():
    session.clear() # Clear the session
    return redirect(url_for('login')) # Redirect to login page

# Add headers to responses to control caching
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Function to get the current logged-in user
def get_current_user():
    if "username" in session:
        return db.session.query(User).filter_by(email=session["username"]).one_or_none()
    return None

# Run the Flask application
if __name__ == "__main__":
    app.run(debug=True)