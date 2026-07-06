from sqlalchemy import text 
from datetime import datetime, date 

def query_db(db_instance, query_string, args=None, one=False):
    """
    Executes a raw SQL SELECT query using Flask-SQLAlchemy's session.
    This function is now solely for raw SQL queries, aligning with __init__.py's usage.

    :param db_instance: The Flask-SQLAlchemy 'db' instance.
    :param query_string: The raw SQL query string (e.g., "SELECT * FROM my_table WHERE id = :my_id").
    :param args: A dictionary of parameters for named placeholders in the SQL query (e.g., {'my_id': 123}).
                 If your query uses positional placeholders (e.g., '?'), you might need to adjust SQLAlchemy's
                 dialect settings or convert to named parameters.
    :param one: If True, return only the first row (as a dictionary, or None if no results).
                If False, return a list of dictionaries.
    :return: List of dictionaries (or a single dictionary if one=True).
    """
    if args is None:
        args = {} 

    try:

        result = db_instance.session.execute(text(query_string), args).fetchall()

        rows_as_dicts = [dict(row._mapping) for row in result]

        final_results = []
        for row_dict in rows_as_dicts:
            processed_row = {}
            for key, value in row_dict.items():
                if isinstance(value, (datetime, date)):
                    processed_row[key] = value.isoformat() 
                else:
                    processed_row[key] = value
            final_results.append(processed_row)

        return (final_results[0] if final_results else None) if one else final_results
    except Exception as e:

        print(f"ERROR executing raw query '{query_string}' with args {args}: {e}", file=sys.stderr)

        return [] 

def query_db_paginated(db_instance, query_string, page_num, per_page, args=None):
    """
    Executes a paginated raw SQL SELECT query using Flask-SQLAlchemy's session.
    This function is now solely for paginated raw SQL queries.

    :param db_instance: The Flask-SQLAlchemy 'db' instance.
    :param query_string: The base raw SQL query string (e.g., "SELECT * FROM my_table WHERE ...").
                         DO NOT include LIMIT or OFFSET clauses here; they will be added.
    :param page_num: Current page number (1-indexed).
    :param per_page: Number of items to return per page.
    :param args: A dictionary of parameters for named placeholders in the SQL query.
    :return: List of dictionaries for the paginated results.
    """
    if args is None:
        args = {}

    offset = (page_num - 1) * per_page

    paginated_query_str = f"{query_string} LIMIT :limit OFFSET :offset"

    pag_args = args.copy()
    pag_args['limit'] = per_page
    pag_args['offset'] = offset

    try:

        result = db_instance.session.execute(text(paginated_query_str), pag_args).fetchall()
        rows_as_dicts = [dict(row._mapping) for row in result]

        final_results = []
        for row_dict in rows_as_dicts:
            processed_row = {}
            for key, value in row_dict.items():
                if isinstance(value, (datetime, date)):
                    processed_row[key] = value.isoformat()
                else:
                    processed_row[key] = value
            final_results.append(processed_row)

        return final_results
    except Exception as e:
        print(f"ERROR executing paginated raw query '{query_string}' with args {pag_args}: {e}", file=sys.stderr)
        return []

def update_db(db_instance, query_string, params=None):
    """
    Executes an UPDATE, INSERT, or DELETE raw SQL query using Flask-SQLAlchemy's session.
    This function's signature now matches how it's called in __init__.py.

    :param db_instance: The Flask-SQLAlchemy 'db' instance.
    :param query_string: The complete raw SQL query string (e.g., "UPDATE my_table SET name = :new_name WHERE id = :row_id").
    :param params: A dictionary (for named placeholders) or a tuple/list (for positional placeholders)
                   of parameters for the SQL query.
    :return: True if the update was successful and committed, False otherwise.
    """

    if params is None:
        params = {} 

    try:

        if isinstance(params, dict):
            db_instance.session.execute(text(query_string), params)
        else: 
            db_instance.session.execute(text(query_string), *params) 

        db_instance.session.commit() 
        return True
    except Exception as e:
        db_instance.session.rollback() 
        print(f"ERROR executing update query '{query_string}' with params {params}: {e}", file=sys.stderr)
        return False