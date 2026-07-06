import db_management
from flask import g
import sqlite3
from __init__ import *

query_str_1 = """
    UPDATE Flora 
    SET Genus = 'Acacia', Species = 'test name', Taxonomy_Family = 'Fabaceae', Common_Name = 'test name', Location_Name = 'Reserve', 
        Conservation_Status = 'test', 'Listed_R&E' = 'No', 'Locally_R&E' = 'Yes', Native = 'No', 
        File = 'file1', Year = 2024
    WHERE ID = 88
    """

query_str_2 = """
    UPDATE Flora 
    SET Genus = 'Acacia', Species = 'echinula', Taxonomy_Family = 'Fabaceae - mimosoideae', Common_Name = 'Hedgehog wattle', Location_Name = 'Dilke Reserve', 
        Conservation_Status = 'V1', 'Listed_R&E' = 'Yes', 'Locally_R&E' = 'Yes', Native = '', 
        File = 'Southern Reserves Flora&Fauna Apndx4 POM', Year = 2004
    WHERE ID = 88
    """

with app.app_context():
    db_management.update_db(query_str_1)
    db_management.update_db(query_str_2)

    result = db_management.query_db("SELECT * FROM Flora;")

    if "db" not in g:
        g.db = sqlite3.connect('Database2.db')
        g.db.row_factory = sqlite3.Row

    conn = g.db
    cursor = conn.cursor()
    values = cursor.execute("SELECT * FROM Flora;")
    keys = []
    for i in values.description:
        keys.append(i[0])
    keys = tuple(keys)
    list_dict = []
    try:
        for i in values:
            dictionary = dict(zip(keys,i))
            list_dict.append(dictionary)
    except:
        dictionary = dict(zip(keys,values))
        list_dict.append(dictionary)
    #result = conn.fetchall()
    cursor.close()
    result1 = list_dict

    diff = False
    for i in range(len(result)):
        if result[i]['Genus'] != result[i]['Genus']:
            print(i, result[i]['Genus'] + " " + result[i]['Genus'])
            diff = True
        if result[i]['Species'] != result[i]['Species']:
            print(i, result[i]['Species'] + " " + result[i]['Species'])
            diff = True
        if result[i]['Genus'] != result[i]['Genus']:
            print(i, result[i]['Taxonomy_Family'] + " " + result[i]['Taxonomy_Family'])
            diff = True
        if result[i]['Taxonomy_Family'] != result[i]['Taxonomy_Family']:
            print(i, result[i]['Genus'] + " " + result[i]['Genus'])
            diff = True
        if result[i]['Common_Name'] != result[i]['Common_Name']:
            print(i, result[i]['Common_Name'] + " " + result[i]['Common_Name'])
            diff = True
        if result[i]['Location_Name'] != result[i]['Location_Name']:
            print(i, result[i]['Location_Name'] + " " + result[i]['Location_Name'])
            diff = True
        if result[i]['Conservation_Status'] != result[i]['Conservation_Status']:
            print(i, result[i]['Conservation_Status'] + " " + result[i]['Conservation_Status'])
            diff = True
        if result[i]['Listed_R&E'] != result[i]['Listed_R&E']:
            print(i, result[i]['Listed_R&E'] + " " + result[i]['Listed_R&E'])
            diff = True
        if result[i]['Locally_R&E'] != result[i]['Locally_R&E']:
            print(i, result[i]['Locally_R&E'] + " " + result[i]['Locally_R&E'])
            diff = True
        if result[i]['Native'] != result[i]['Native']:
            print(i, result[i]['Native'] + " " + result[i]['Native'])
            diff = True
        if result[i]['File'] != result[i]['File']:
            print(i, result[i]['File'] + " " + result[i]['File'])
            diff = True
        if result[i]['Year'] != result[i]['Year']:
            print(i, result[i]['Year'] + " " + result[i]['Year'])
            diff = True
    print(diff)