import unittest
from unittest.mock import patch
from flask import Flask, template_rendered
from __init__ import *
import db_management
from contextlib import contextmanager

# coverage run -m unittest appTesting.py
# coverage html

@contextmanager
def captured_templates(app):
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)

DATABASE = "Database_Test.db"
USER_DATABASE = "users.db"

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        # Set up the test client and the test environment
        self.client = app.test_client()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing if using Flask-WTF  

    def test_index(self):
        self.client.get('/logout')
        response = self.client.get('/', follow_redirects=True)
        self.assertIn(b'login', response.data)  # Should redirect to the login page

    @patch('__init__.send_email')
    def test_forget_and_reset_password(self, mock_send_email):
        self.client.get('/logout')
        response = self.client.get('/forgot-password', follow_redirects=True)
        self.assertIn(b'Forgot Password', response.data)

        response = self.client.post('/forgot-password', data={
            'email': 'invalidemail@gmail.com'
        }, follow_redirects=True)
        # self.assertIn(b'Invalid email address.', response.data)

        response = self.client.post('/forgot-password', data={
            'email': 'admin@test.com'
        }, follow_redirects=True)
        self.assertIn(b"""Password reset link 
                               has been sent to your email address.""", response.data)


        with app.app_context():
            args, _ = mock_send_email.call_args
            email_content = args[2]

            token_start = email_content.find('reset_password/') + len('reset_password/')
            token_end = email_content.find('">', token_start)
            token = email_content[token_start:token_end]

        #invalid token
        response = self.client.get('/reset_password/token', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)
        #valid token
        response = self.client.get('/reset_password/'+token, follow_redirects=True)
        self.assertIn(b'Reset Password', response.data)

        response = self.client.post('/reset_password/'+token, data={
            'password': 'newpwd'
        }, follow_redirects=True)
        self.assertIn(b'Password has been reset.', response.data)

        #Change the password back
        response = self.client.post('/reset_password/'+token, data={
            'password': 'pwd'
        })

    def test_login_admin_success(self):
        self.client.get('/logout')
        response = self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)  # Should redirect after successful login
        
        self.assertTrue(session['logged_in'])
        self.assertEqual(session['username'], 'admin@test.com')
        self.assertTrue(session['is_admin'])
        self.assertIn(b'Dashboard', response.data)

        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

        response = self.client.get('/login', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)

    def test_login_user_success(self):
        self.client.get('/logout')
        response = self.client.post('/login', data={
            'username': 'ywan4079@uni.sydney.edu.au',
            'password': 'password'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)  # Should redirect after successful login
        
        self.assertTrue(session['logged_in'])
        self.assertEqual(session['username'], 'ywan4079@uni.sydney.edu.au')
        self.assertFalse(session['is_admin'])
        self.assertIn(b'Dashboard', response.data)

        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

        response = self.client.get('/login', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)

    def test_login_failure(self):
        self.client.get('/logout')
        response = self.client.post('/login', data={
            'username': 'invalid user',
            'password': 'invalid pwd'
        })
        self.assertIn(b"""Username or password
                                   is incorrect.""", response.data)
        self.assertEqual(response.status_code, 200)

    def test_setting_admin(self):
        self.client.get('/logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        response = self.client.get('/settings', follow_redirects=True)
        self.assertIn(b'Settings', response.data)
        with self.client as c:
            with captured_templates(app) as templates:
                r = c.get('/settings')
                template, context = templates[0]
                self.assertTrue(context['is_admin'])

    def test_setting_user(self):
        self.client.get('/logout')
        self.client.post('/login', data={
            'username': 'ywan4079@uni.sydney.edu.au',
            'password': 'password'
        })
        with self.client as c:
                with captured_templates(app) as templates:
                    r = c.get('/settings')
                    template, context = templates[0]
                    self.assertFalse(context['is_admin'])

    @patch('__init__.send_email')
    def test_valid_signup(self, mock_send_email):
        self.client.get('/logout')
        response = self.client.post('/signup', data={
            'username': 'user@test.com',
            'password': 'pwd',
            'confirm_password': 'pwd'
        }, follow_redirects=True)
        self.assertIn(b"""Confirmation link 
                               has been sent to your email address. Please 
                               verify your account before logging in.""", response.data)

        with app.app_context():
            args, _ = mock_send_email.call_args
            email_content = args[2]

            token_start = email_content.find('confirm/') + len('confirm/')
            token_end = email_content.find('">', token_start)
            token = email_content[token_start:token_end]
        
        #try to log in without verification
        response = self.client.post('/login', data={
            'username': 'user@test.com',
            'password': 'pwd',
        }, follow_redirects=True)
        self.assertIn(b"""Your account has not 
                                   been verified, please follow the confirmation 
                                   link in your email inbox.""", response.data)
        
        #Invalid token
        response = self.client.get('/confirm/invalidtoken', follow_redirects=True)
        self.assertIn(b"""The confirmation 
                               link is invalid or has expired.""", response.data)
        
        #Valid token
        response = self.client.get('/confirm/'+token, follow_redirects=True)
        self.assertIn(b"""Your account has been 
                               verified.""", response.data)
        
        #Verify again
        response = self.client.get('/confirm/'+token, follow_redirects=True)
        self.assertIn(b"""Your account has already
                                   been verified. Please log in.""", response.data)
        
        #Try log in
        response = self.client.post('/login', data={
            'username': 'user@test.com',
            'password': 'pwd',
        }, follow_redirects=True)
        self.assertTrue(session['logged_in'])
        self.assertEqual(session['username'], 'user@test.com')
        self.assertFalse(session['is_admin'])
        self.assertIn(b'Dashboard', response.data)

        response = self.client.get('/signup', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)

        #Delete user after testing
        with app.app_context():
            email = User.confirm_token(app, token)
            user = db.session.query(User).filter_by(email=email).one_or_none()
            db.session.delete(user)
            db.session.commit()
        
    
    def test_invalid_signup(self):
        self.client.get('/logout')
        response = self.client.get('/signup', follow_redirects=True)
        self.assertIn(b'Register', response.data)

        response = self.client.post('/signup', data={
            'username': 'admin@test.com',
            'password': 'pwd',
            'confirm_password': 'pwd'
        })
        self.assertIn(b'Account already exists', response.data)

        response = self.client.post('/signup', data={
            'username': 'user@test1.com',
            'password': 'pwd',
            'confirm_password': 'pwd1'
        })
        self.assertIn(b'Passwords do not match', response.data)


    def test_flora_dashboard(self):
        self.client.get('/logout')

        response = self.client.get('/flora_dashboard', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)

        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        response = self.client.get('/flora_dashboard', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)
        self.assertIn(b'Flora Results', response.data)
        self.assertIn(b'Planted Native', response.data) #only for flora
        
        #check the header
        self.assertIn(b'<th>Location Name</th>', response.data)
        self.assertIn(b'<th>Genus</th>', response.data)
        self.assertIn(b'<th>Species</th>', response.data)
        self.assertIn(b'<th>Family</th>', response.data)
        self.assertIn(b'<th>Common Name</th>', response.data)
        self.assertIn(b'<th>Conservation Status</th>', response.data)
        self.assertIn(b'<th>Listed R&E</th>', response.data)
        self.assertIn(b'<th>Locally R&E</th>', response.data)
        self.assertIn(b'<th>Native</th>', response.data)
        self.assertIn(b'<th>Year</th>', response.data)
        
        #test options in flora dashboard
        with app.app_context():
            options = get_options_flora()
            for key in options.keys():
                for option in options[key]:
                    self.assertIn(option.encode(), response.data)

    def test_fauna_dashboard(self):
        self.client.get('/logout')

        response = self.client.get('/flora_dashboard', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)

        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        response = self.client.get('/fauna_dashboard', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)
        self.assertIn(b'Fauna Results', response.data)

        #check the header
        self.assertIn(b'<th>Location Name</th>', response.data)
        self.assertIn(b'<th>Genus</th>', response.data)
        self.assertIn(b'<th>Species</th>', response.data)
        self.assertIn(b'<th>Family</th>', response.data)
        self.assertIn(b'<th>Common Name</th>', response.data)
        self.assertIn(b'<th>Class Name</th>', response.data)
        self.assertIn(b'<th>Conservation Status</th>', response.data)
        self.assertIn(b'<th>Listed R&E</th>', response.data)
        self.assertIn(b'<th>Locally R&E</th>', response.data)
        self.assertIn(b'<th>Native</th>', response.data)
        self.assertIn(b'<th>Year</th>', response.data)
        
        #test options in flora dashboard
        with app.app_context():
            options = get_options_fauna()
            for key in options.keys():
                for option in options[key]:
                    option = option.replace('\'','&#39;')
                    self.assertIn(option.encode(), response.data)

    def test_manage_users(self):
        self.client.get('logout')

        response = self.client.get('/manage_users', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)

        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        response = self.client.get('/manage_users', follow_redirects=True)
        self.assertIn(b'Manage Users', response.data)
        with app.app_context():
            users = db_management.query_user_db("SELECT id, email, role FROM users", ())
            for user in users:
                self.assertIn(user['email'].encode(), response.data)
                self.assertIn(user['role'].encode(), response.data)
        
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'ywan4079@uni.sydney.edu.au',
            'password': 'password'
        })
        response = self.client.get('/manage_users', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)      

    def test_edit_users(self):
        self.client.get('logout')

        response = self.client.get('/edit_user/100', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)
        
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        # Invalid ID
        response = self.client.get('/edit_user/10000', follow_redirects=True)
        self.assertIn(b'Manage Users', response.data)


        response = self.client.get('/edit_user/2', follow_redirects=True)
        self.assertIn(b'Edit User', response.data)

        response = self.client.post('/edit_user/2', data={
            'email': 'newemail@test.com',
            'role': 'tester'
        }, follow_redirects=True)
        self.assertIn(b'Manage Users', response.data)

        with app.app_context():
            edited_user = db.session.query(User).filter_by(id=2).one_or_none()
        self.assertEqual(edited_user.email, 'newemail@test.com')
        self.assertEqual(edited_user.role, 'tester')

        # #Change it back
        response = self.client.post('/edit_user/2', data={
            'email': 'ywan4079@uni.sydney.edu.au',
            'role': 'User'
        }, follow_redirects=True)

        # Non admin account
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'ywan4079@uni.sydney.edu.au',
            'password': 'password'
        })

        response = self.client.get('/edit_user/2', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)
    
    @patch('__init__.send_email')
    def test_delete_users(self, mock_send_email):
        #Create testing account
        self.client.get('/logout')
        response = self.client.post('/signup', data={
            'username': 'user@test.com',
            'password': 'pwd',
            'confirm_password': 'pwd'
        }, follow_redirects=True)

        with app.app_context():
            args, _ = mock_send_email.call_args
            email_content = args[2]

            token_start = email_content.find('confirm/') + len('confirm/')
            token_end = email_content.find('">', token_start)
            token = email_content[token_start:token_end]
        
        #Valid token
        response = self.client.get('/confirm/'+token, follow_redirects=True)

        response = self.client.get('/delete_user/100', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)
        
        #Normal user account
        self.client.post('/login', data={
            'username': 'ywan4079@uni.sydney.edu.au',
            'password': 'password'
        })
        response = self.client.get('/delete_user/2', follow_redirects=True)
        self.assertIn(b'Dashboard', response.data)

        #Admin account
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        #Invalid user id
        response = self.client.get('/delete_user/10000', follow_redirects=True)
        self.assertIn(b'Manage Users', response.data)

        #Remove account
        with app.app_context():
            delete_user = db.session.query(User).filter_by(email='user@test.com').one_or_none()
        response = self.client.get('/delete_user/' + str(delete_user.id), follow_redirects=True)
        self.assertIn(b'Manage Users', response.data)

        #Try log in
        self.client.get('logout')
        response = self.client.post('/login', data={
            'username': 'user@test.com',
            'password': 'pwd'
        }, follow_redirects=True)
        self.assertIn(b"""Username or password
                                   is incorrect.""", response.data)

    def test_filter_flora(self):
        self.client.get('logout')

        response = self.client.get('/filter_flora', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)

        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        with app.app_context():
            result = db_management.query_db("""
                                           SELECT * FROM Flora F
                                           WHERE F.Genus = 'Acacia' AND F.Species = 'baileyana' AND F.Taxonomy_Family = 'Fabaceae' 
                                           AND F.Native = 'Planted Native'
                                           """, ())

        with self.client as c:
            with captured_templates(app) as templates:
                response = self.client.post('/filter_flora', data={
                    'genus': 'Acacia',
                    'family': 'Fabaceae',
                    'species': 'baileyana',
                    'reserve': 'Thomas Street Depot',
                    'selected_reserves_input': 'Montgomery Reserve,The River Reserve',
                    'native': 'PNative',
                    'rare': ''
                })
                template, context = templates[0]

                self.assertEqual(context['genus'], 'Acacia')
                self.assertEqual(context['family'], 'Fabaceae')
                self.assertEqual(context['species'], 'baileyana')
                self.assertListEqual(context['selected_reserves'], ['Montgomery Reserve', 'The River Reserve', 'Thomas Street Depot'])
                self.assertEqual(context['native'], 'PNative')
                self.assertEqual(context['rare'], '')
                self.assertTrue(context['is_flora'])

                self.assertTrue(len(context['genusOptions']) == 1 and context['genusOptions'][0] == 'Acacia')
                self.assertTrue(len(context['familyOptions']) == 1 and context['familyOptions'][0] == 'Fabaceae')
                self.assertTrue(len(context['speciesOptions']) == 1 and context['speciesOptions'][0] == 'baileyana')
                
                reserveOptions = sorted(list(set(row['Location_Name'] for row in result)))
                for selectedReserve in ['Montgomery Reserve', 'The River Reserve', 'Thomas Street Depot']:
                    if selectedReserve in reserveOptions:
                        reserveOptions.remove(selectedReserve)

                result = db_management.query_db("""
                                           SELECT * FROM Flora F
                                           WHERE F.Genus = 'Acacia' AND F.Species = 'baileyana' AND F.Taxonomy_Family = 'Fabaceae' 
                                           AND F.Native = 'Planted Native' 
                                            AND F.Location_Name IN ('Montgomery Reserve', 'The River Reserve', 'Thomas Street Depot')
                                           """, ())

                self.assertListEqual(reserveOptions, context['reserveOptions'])
                for i in range(len(result)):
                    self.assertEqual(result[i]['Genus'], context['filtered_result'][i]['Genus'])
                    self.assertEqual(result[i]['Species'], context['filtered_result'][i]['Species'])
                    self.assertEqual(result[i]['Taxonomy_Family'], context['filtered_result'][i]['Taxonomy_Family'])
                    self.assertEqual(result[i]['Common_Name'], context['filtered_result'][i]['Common_Name'])
                    self.assertEqual(result[i]['Location_Name'], context['filtered_result'][i]['Location_Name'])
                    self.assertEqual(result[i]['Conservation_Status'], context['filtered_result'][i]['Conservation_Status'])
                    self.assertEqual(result[i]['Listed_R&E'], context['filtered_result'][i]['Listed_R&E'])
                    self.assertEqual(result[i]['Locally_R&E'], context['filtered_result'][i]['Locally_R&E'])
                    self.assertEqual(result[i]['Native'], context['filtered_result'][i]['Native'])
                    self.assertEqual(result[i]['File'], context['filtered_result'][i]['File'])
                    self.assertEqual(result[i]['Form'], context['filtered_result'][i]['Form'])
                    self.assertEqual(result[i]['Year'], context['filtered_result'][i]['Year'])

    def test_filter_fauna(self):
        self.client.get('logout')

        response = self.client.get('/filter_fauna', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)

        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        with app.app_context():
            result = db_management.query_db("""
                                           SELECT * FROM Fauna F
                                           WHERE F.Genus = 'Acanthiza' AND F.Species = 'chrysorrhoa' AND F.Taxonomy_Family = 'Acanthizidae' 
                                           AND F.Native = '' AND F.'Listed_R&E' = 'Yes'
                                           """, ())

        with self.client as c:
            with captured_templates(app) as templates:
                response = self.client.post('/filter_fauna', data={
                    'genus': 'Acanthiza',
                    'family': 'Acanthizidae',
                    'species': 'chrysorrhoa',
                    'reserve': 'M5 Bridge over Salt Pan Creek',
                    'selected_reserves_input': 'Deepwater,Irrambeena',
                    'native': 'Native',
                    'rare': 'listed-rare'
                })
                template, context = templates[0]

                self.assertEqual(context['genus'], 'Acanthiza')
                self.assertEqual(context['family'], 'Acanthizidae')
                self.assertEqual(context['species'], 'chrysorrhoa')
                self.assertListEqual(context['selected_reserves'], ['Deepwater', 'Irrambeena', 'M5 Bridge over Salt Pan Creek'])
                self.assertEqual(context['native'], 'Native')
                self.assertEqual(context['rare'], 'Listed Rare')
                self.assertFalse(context['is_flora'])

                self.assertTrue(len(context['genusOptions']) == 1 and context['genusOptions'][0] == 'Acanthiza')
                self.assertTrue(len(context['familyOptions']) == 1 and context['familyOptions'][0] == 'Acanthizidae')
                self.assertTrue(len(context['speciesOptions']) == 1 and context['speciesOptions'][0] == 'chrysorrhoa')
                
                reserveOptions = sorted(list(set(row['Location_Name'] for row in result)))
                for selectedReserve in ['Deepwater', 'Irrambeena', 'M5 Bridge over Salt Pan Creek']:
                    if selectedReserve in reserveOptions:
                        reserveOptions.remove(selectedReserve)

                result = db_management.query_db("""
                                           SELECT * FROM Fauna F
                                           WHERE F.Genus = 'Acanthiza' AND F.Species = 'chrysorrhoa' AND F.Taxonomy_Family = 'Acanthizidae' 
                                           AND F.Native = '' AND F.'Listed_R&E' = 'Yes'
                                            AND F.Location_Name IN ('Deepwater', 'Irrambeena', 'M5 Bridge over Salt Pan Creek')
                                           """, ())

                self.assertListEqual(reserveOptions, context['reserveOptions'])
                for i in range(len(result)):
                    self.assertEqual(result[i]['Genus'], context['filtered_result'][i]['Genus'])
                    self.assertEqual(result[i]['Species'], context['filtered_result'][i]['Species'])
                    self.assertEqual(result[i]['Taxonomy_Family'], context['filtered_result'][i]['Taxonomy_Family'])
                    self.assertEqual(result[i]['Common_Name'], context['filtered_result'][i]['Common_Name'])
                    self.assertEqual(result[i]['Class_Name'], context['filtered_result'][i]['Class_Name'])
                    self.assertEqual(result[i]['Location_Name'], context['filtered_result'][i]['Location_Name'])
                    self.assertEqual(result[i]['Conservation_Status'], context['filtered_result'][i]['Conservation_Status'])
                    self.assertEqual(result[i]['Listed_R&E'], context['filtered_result'][i]['Listed_R&E'])
                    self.assertEqual(result[i]['Locally_R&E'], context['filtered_result'][i]['Locally_R&E'])
                    self.assertEqual(result[i]['Native'], context['filtered_result'][i]['Native'])
                    self.assertEqual(result[i]['File'], context['filtered_result'][i]['File'])
                    self.assertEqual(result[i]['Year'], context['filtered_result'][i]['Year'])

    def test_update_data(self):
        self.client.get('logout')

        response = self.client.get('/update_data', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)

        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        response = self.client.get('/update_data', follow_redirects=True)
        self.assertTrue(session['edit_mode'])
        self.assertIn(b'Dashboard', response.data)

        response = self.client.get('/update_data', follow_redirects=True)
        self.assertFalse(session['edit_mode'])
        self.assertIn(b'Dashboard', response.data)

    def test_report_get(self):
        self.client.get('logout')

        response = self.client.get('/report', follow_redirects=True)
        self.assertIn(b'Login Page - Canterbury Bankstown', response.data)

        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        with self.client as c:
            with captured_templates(app) as templates:
                response = c.get('/report', follow_redirects=True)
                self.assertIn(b'Report Page', response.data)
                template, context = templates[0]
                self.assertEqual(context['username'], 'admin@test.com')
                self.assertTrue(context['is_admin'])
                self.assertIsNotNone(context['result'])
                self.assertEqual(context['report'], 'All Species')
                self.assertEqual(context['report_type'], 'Flora')
                self.assertTrue(context['is_flora'])
    
    def test_report_post(self):
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        with self.client as c:
            with captured_templates(app) as templates:
                response = c.post('/report', data={
                    'report_type': 'Fauna',
                    'report_name': 'Summary Report'
                },follow_redirects=True)
                self.assertIn(b'Report Page', response.data)
                template, context = templates[0]
                self.assertEqual(context['username'], 'admin@test.com')
                self.assertTrue(context['is_admin'])
                self.assertIsNotNone(context['result'])
                self.assertEqual(context['report'], 'Summary Report')
                self.assertEqual(context['report_type'], 'Fauna')
                self.assertFalse(context['is_flora'])
                
    def test_report_post_none(self):
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        with self.client as c:
            with captured_templates(app) as templates:
                response = c.post('/report', data={
                    'report_type': 'Fauna',
                    'report_name': 'Native Flora = 1 Site'
                },follow_redirects=True)
                self.assertIn(b'Report Page', response.data)
                template, context = templates[0]
                self.assertEqual(context['username'], 'admin@test.com')
                self.assertTrue(context['is_admin'])
                self.assertIsNone(context['result'])
                self.assertEqual(context['report'], 'Native Flora = 1 Site')
                self.assertEqual(context['report_type'], 'Fauna')
                self.assertFalse(context['is_flora'])

    def test_download(self):
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        response = self.client.post('/download', data={
                    'report_type': 'Flora',
                    'report_name': 'All Species'
                })
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/download', data={
                    'report_type': 'Flora',
                    'report_name': 'Native Flora = 1 Site'
                })
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/download', data={
                    'report_type': 'Fauna',
                    'report_name': 'Summary Report'
                })
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/download', data={
                    'report_type': 'Fauna',
                    'report_name': 'Native Flora = 1 Site'
                })
        self.assertEqual(response.status_code, 400)

        response = self.client.post('/download', data={
                    'report_type': '',
                    'report_name': ''
                })
        self.assertEqual(response.status_code, 400)

    def test_logout(self):
        self.client.get('logout')
        self.assertFalse('is_admin' in session)
        self.assertFalse('edit_mode' in session)
        self.assertFalse('logged_in' in session)
        self.assertFalse('username' in session)



    def test_save_table_flora_single(self):
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        data = {
            'originalData': {
                'ID': 56,
                'Genus': 'Acacia',
                'Species': 'echinula',
                'Family': 'Fabaceae (mimosoideae)',
                'Common_Name': 'Hedgehog wattle',
                'Location_Name': 'Dilke Reserve',
                'Conservation_Status': 'V1',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Southern Reserves Flora&Fauna Apndx4 POM',
                'Year': 2004
            },
            'newData': {
                'Genus': 'Acacia',
                'Species': 'test name',
                'Family': 'Fabaceae',
                'Common_Name': 'test name',
                'Location_Name': 'Reserve',
                'Conservation_Status': 'test',
                'Listed_R&E': 'No',
                'Locally_R&E': 'Yes',
                'Native': 'No',
                'File': 'file1',
                'Year': 2024
            },
            'replaceAll': []
        }
        response = self.client.post('/save_table_flora', json=data, follow_redirects=True)
        with app.app_context():
            result = db_management.query_db("SELECT * FROM Flora F WHERE ID = 56")[0]
            self.assertEqual(result['Genus'], 'Acacia')
            self.assertEqual(result['Species'], 'test name')
            self.assertEqual(result['Taxonomy_Family'], 'Fabaceae')
            self.assertEqual(result['Common_Name'], 'test name')
            self.assertEqual(result['Location_Name'], 'Reserve')
            self.assertEqual(result['Conservation_Status'], 'test')
            self.assertEqual(result['Listed_R&E'], 'No')
            self.assertEqual(result['Locally_R&E'], 'Yes')
            self.assertEqual(result['Native'], 'No')
            self.assertEqual(result['File'], 'file1')
            self.assertEqual(result['Year'], '2024')
        data = {
            'newData': {
                'Genus': 'Acacia',
                'Species': 'echinula',
                'Family': 'Fabaceae (mimosoideae)',
                'Common_Name': 'Hedgehog wattle',
                'Location_Name': 'Dilke Reserve',
                'Conservation_Status': 'V1',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Southern Reserves Flora&Fauna Apndx4 POM',
                'Year': 2004
            },
            'originalData': {
                'ID': 56,
                'Genus': 'Acacia',
                'Species': 'test name',
                'Family': 'Fabaceae',
                'Common_Name': 'test name',
                'Location_Name': 'Reserve',
                'Conservation_Status': 'test',
                'Listed_R&E': 'No',
                'Locally_R&E': 'Yes',
                'Native': 'No',
                'File': 'file1',
                'Year': 2024
            },
            'replaceAll': []
        }
        #Change the dataset back
        response = self.client.post('/save_table_flora', json=data)

    def test_save_table_flora_all(self):
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        with app.app_context():
            original = db_management.query_db("SELECT ID FROM Flora WHERE Species = ?", ('decurrens',))
            ids = [row['ID'] for row in original]

        data = {
            'originalData': {
                'ID': 25,
                'Genus': 'Acacia',
                'Species': 'decurrens',
                'Family': 'Fabaceae (mimosoideae)',
                'Common_Name': 'Black wattle, early black-wattle',
                'Location_Name': 'Walshaw Park',
                'Conservation_Status': '',
                'Listed_R&E': '',
                'Locally_R&E': '',
                'Native': '',
                'File': 'Walshaw Flora&Fauna Apndx4 POM',
                'Year': 2004
            },
            'newData': {
                'Genus': 'Acacia',
                'Species': 'new species',
                'Family': 'Fabaceae - mimosoideae',
                'Common_Name': 'Black wattle, early black-wattle',
                'Location_Name': 'Walshaw Park',
                'Conservation_Status': '',
                'Listed_R&E': '',
                'Locally_R&E': '',
                'Native': '',
                'File': 'Walshaw Flora&Fauna Apndx4 POM',
                'Year': 2004
            },
            'replaceAll': ['Species']
        }
        
        response = self.client.post('/save_table_flora', json=data)

        with app.app_context():
            id_string = ', '.join(map(str, ids))
            result = db_management.query_db(f"SELECT * FROM Flora F WHERE ID IN ({id_string})")
            for row in result:
                self.assertEqual(row['Species'], 'new species')

        data = {
            'newData': {
                'Genus': 'Acacia',
                'Species': 'decurrens',
                'Family': 'Fabaceae (mimosoideae)',
                'Common_Name': 'Black wattle, early black-wattle',
                'Location_Name': 'Walshaw Park',
                'Conservation_Status': '',
                'Listed_R&E': '',
                'Locally_R&E': '',
                'Native': '',
                'File': 'Walshaw Flora&Fauna Apndx4 POM',
                'Year': 2004
            },
            'originalData': {
                'ID': 25,
                'Genus': 'Acacia',
                'Species': 'new species',
                'Family': 'Fabaceae - mimosoideae',
                'Common_Name': 'Black wattle, early black-wattle',
                'Location_Name': 'Walshaw Park',
                'Conservation_Status': '',
                'Listed_R&E': '',
                'Locally_R&E': '',
                'Native': '',
                'File': 'Walshaw Flora&Fauna Apndx4 POM',
                'Year': 2004
            },
            'replaceAll': ['Species']
        }
        # Change the dataset back
        response = self.client.post('/save_table_flora', json=data)


    def test_save_table_fauna_single(self):
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })
        data = {
            'originalData': {
                'ID': 17,
                'Genus': 'Acanthiza',
                'Species': 'nana',
                'Family': '	Acanthizidae',
                'Common_Name': 'Yellow thornbill',
                'Class_Name': 'Aves',
                'Location_Name': 'Deepwater',
                'Conservation_Status': 'r',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Deepwater Flora&Fauna Apndx5 POM',
                'Year': 2004
            },
            'newData': {
                'Genus': 'Acanthiza1',
                'Species': 'test name',
                'Family': 'Acanthizidae1',
                'Common_Name': 'Yellow thornbill1',
                'Class_Name': 'Aves1',
                'Location_Name': 'Reserve',
                'Conservation_Status': 'test',
                'Listed_R&E': 'No',
                'Locally_R&E': 'Yes',
                'Native': 'No',
                'File': 'file1',
                'Year': 2024
            },
            'replaceAll': []
        }
        response = self.client.post('/save_table_fauna', json=data)
        with app.app_context():
            result = db_management.query_db("SELECT * FROM Fauna WHERE ID = 17")[0]
            self.assertEqual(result['Genus'], 'Acanthiza1')
            self.assertEqual(result['Species'], 'test name')
            self.assertEqual(result['Taxonomy_Family'], 'Acanthizidae1')
            self.assertEqual(result['Common_Name'], 'Yellow thornbill1')
            self.assertEqual(result['Class_Name'], 'Aves1')
            self.assertEqual(result['Location_Name'], 'Reserve')
            self.assertEqual(result['Conservation_Status'], 'test')
            self.assertEqual(result['Listed_R&E'], 'No')
            self.assertEqual(result['Locally_R&E'], 'Yes')
            self.assertEqual(result['Native'], 'No')
            self.assertEqual(result['File'], 'file1')
            self.assertEqual(result['Year'], '2024')
        data = {
            'newData': {
                'Genus': 'Acanthiza',
                'Species': 'nana',
                'Family': '	Acanthizidae',
                'Common_Name': 'Yellow thornbill',
                'Class_Name': 'Aves',
                'Location_Name': 'Deepwater',
                'Conservation_Status': 'r',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Deepwater Flora&Fauna Apndx5 POM',
                'Year': 2004
            },
            'originalData': {
                'ID': 17,
                'Genus': 'Acanthiza1',
                'Species': 'test name',
                'Family': 'Acanthizidae1',
                'Common_Name': 'Yellow thornbill1',
                'Class_Name': 'Aves1',
                'Location_Name': 'Reserve',
                'Conservation_Status': 'test',
                'Listed_R&E': 'No',
                'Locally_R&E': 'Yes',
                'Native': 'No',
                'File': 'file1',
                'Year': 2024
            },
            'replaceAll': []
        }
        #Change the dataset back
        response = self.client.post('/save_table_flora', json=data)

    def test_save_table_fauna_all(self):
        self.client.get('logout')
        self.client.post('/login', data={
            'username': 'admin@test.com',
            'password': 'pwd'
        })

        with app.app_context():
            original = db_management.query_db("SELECT ID FROM Fauna WHERE Species = ?", ('nana',))
            ids = [row['ID'] for row in original]

        data = {
            'originalData': {
                'ID': 17,
                'Genus': 'Acanthiza',
                'Species': 'nana',
                'Family': 'Acanthizidae',
                'Common_Name': 'Yellow thornbill',
                'Class_Name': 'Aves',
                'Location_Name': 'Deepwater',
                'Conservation_Status': 'r',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Deepwater Flora&Fauna Apndx5 POM',
                'Year': 2004
            },
            'newData': {
                'Genus': 'Acanthiza',
                'Species': 'nana1',
                'Family': 'Acanthizidae',
                'Common_Name': 'Yellow thornbill',
                'Class_Name': 'Aves',
                'Location_Name': 'Deepwater',
                'Conservation_Status': 'r',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Deepwater Flora&Fauna Apndx5 POM',
                'Year': 2004
            },
            'replaceAll': ['Species']
        }

        response = self.client.post('/save_table_fauna', json=data)

        with app.app_context():
            id_string = ', '.join(map(str, ids))
            result = db_management.query_db(f"SELECT * FROM Fauna WHERE ID IN ({id_string})")
            for row in result:
                self.assertEqual(row['Species'], 'nana1')
        data = {
            'newData': {
                'Genus': 'Acanthiza',
                'Species': 'nana',
                'Family': '	Acanthizidae',
                'Common_Name': 'Yellow thornbill',
                'Class_Name': 'Aves',
                'Location_Name': 'Deepwater',
                'Conservation_Status': 'r',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Deepwater Flora&Fauna Apndx5 POM',
                'Year': 2004
            },
            'originalData': {
                'ID': 17,
                'Genus': 'Acanthiza',
                'Species': 'nana1',
                'Family': 'Acanthizidae',
                'Common_Name': 'Yellow thornbill',
                'Class_Name': 'Aves',
                'Location_Name': 'Deepwater',
                'Conservation_Status': 'r',
                'Listed_R&E': 'Yes',
                'Locally_R&E': 'Yes',
                'Native': '',
                'File': 'Deepwater Flora&Fauna Apndx5 POM',
                'Year': 2004
            },
            'replaceAll': ['Species']
        }
        #Change the dataset back
        response = self.client.post('/save_table_fauna', json=data)



    def test_update_user_db(self):
        with app.app_context():
            success = db_management.update_user_db("""UPDATE users
                                         SET email = ?
                                         WHERE id = 2""", ('testemail@test.com',))
            result = db_management.query_user_db("SELECT email FROM users WHERE id = 2")

            self.assertTrue(success)
            self.assertEqual(result[0]['email'], 'testemail@test.com')

            db_management.update_user_db("""UPDATE users
                                         SET email = ?
                                         WHERE id = 2""", ('ywan4079@uni.sydney.edu.au',))
