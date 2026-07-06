from models import Occurrence, Species, Reserve, DataSource, LocalSpeciesInfo, ClientBusiness, Family, Fauna
from User import User
from sqlalchemy import text, func, distinct, and_, cast, String, case
from datetime import datetime, date
import sys

# General Filter Option Retrieval Functions

def get_unique_species(db_session):
    # Retrieve unique scientific names of flora species
    unique_species = db_session.query(Species.scientific_name).distinct().all()
    # Return a list, filtering out None values
    return [s.scientific_name for s in unique_species if s.scientific_name is not None]

def get_unique_reserves(db_session):
    # Retrieve unique reserve names for flora
    unique_reserves = db_session.query(Reserve.reserve_name).distinct().all()
    # Return a list, filtering out None values
    return [r.reserve_name for r in unique_reserves if r.reserve_name is not None]

def get_unique_datasets_with_coords(db_session):
    # Retrieve unique dataset names for occurrences with coordinates
    datasets = db_session.query(Occurrence.dataset_name)\
                             .filter(Occurrence.decimal_latitude.isnot(None),
                                     Occurrence.decimal_longitude.isnot(None))\
                             .distinct()\
                             .all()
    # Return a list, filtering out None values
    return [d.dataset_name for d in datasets if d.dataset_name is not None]

def get_unique_planted_natives(db_session):
    # Retrieve unique 'planted native' statuses
    planted_natives = db_session.query(LocalSpeciesInfo.planted_native)\
                                 .filter(LocalSpeciesInfo.planted_native.isnot(None))\
                                 .distinct()\
                                 .all()
    # Return a list, filtering out None values
    return [pn.planted_native for pn in planted_natives if pn.planted_native is not None]

def get_unique_years(db_session):
    # Retrieve unique years from Occurrence data
    years = db_session.query(Occurrence.year)\
                             .filter(Occurrence.year.isnot(None))\
                             .distinct()\
                             .order_by(Occurrence.year.desc())\
                             .all()
    # Return a list, filtering out None values
    return [y.year for y in years if y.year is not None]

def get_unique_localities(db_session):
    # Retrieve unique localities from Occurrence data
    localities = db_session.query(Occurrence.locality).distinct().all()
    # Return a list, filtering out None values
    return [loc.locality for loc in localities if loc.locality is not None]

def get_unique_habitats(db_session):
    # Retrieve unique habitats from Occurrence data
    habitats = db_session.query(Occurrence.habitat).distinct().all()
    # Return a list, filtering out None values
    return [hab.habitat for hab in habitats if hab.habitat is not None]

def get_unique_basis_of_record(db_session):
    # Retrieve unique basis of record values
    basis_of_record_options = db_session.query(Occurrence.basis_of_record).distinct().all()
    # Return a list, filtering out None values
    return [basis.basis_of_record for basis in basis_of_record_options if basis.basis_of_record is not None]

def get_unique_threatened_species_statuses(db_session):
    # Retrieve unique threatened species statuses
    statuses = db_session.query(Species.threatened_species_status)\
                             .filter(Species.threatened_species_status.isnot(None))\
                             .distinct()\
                             .order_by(Species.threatened_species_status)\
                             .all()
    # Return a list
    return [s.threatened_species_status for s in statuses]

def get_unique_owner_institution_codes(db_session):
    # Retrieve unique owner institution codes
    owner_codes = db_session.query(Occurrence.owner_institution_code)\
                             .filter(Occurrence.owner_institution_code.isnot(None))\
                             .distinct()\
                             .order_by(Occurrence.owner_institution_code)\
                             .all()
    # Return a list, filtering out None values
    return [code.owner_institution_code for code in owner_codes if code.owner_institution_code is not None]

def get_unique_datasets(db_session):
    # Retrieve unique dataset names
    datasets = db_session.query(Occurrence.dataset_name)\
                         .distinct()\
                         .order_by(Occurrence.dataset_name)\
                         .all()
    # Return a list, filtering out None values
    return [d.dataset_name for d in datasets if d.dataset_name is not None]

def get_options_occurrences(db_session):
    # Aggregate all filter options for flora occurrences
    return {
        "speciesOptions": sorted(get_unique_species(db_session)),
        "datasetOptions": sorted(get_unique_datasets(db_session)),
        "reserveOptions": sorted(get_unique_reserves(db_session)),
        "localityOptions": sorted(get_unique_localities(db_session)),
        "habitatOptions": sorted(get_unique_habitats(db_session)),
        "basisOptions": sorted(get_unique_basis_of_record(db_session)),
        "plantedNativeOptions": sorted(get_unique_planted_natives(db_session)),
        "yearOptions": sorted(get_unique_years(db_session)),
        "ownerInstitutionCodeOptions": sorted(get_unique_owner_institution_codes(db_session)),
        "threatenedStatusOptions": sorted(get_unique_threatened_species_statuses(db_session))
    }

def get_observations_query(db_session, species=None, dataset=None, reserve=None,
                           locality=None, habitat=None, basis_of_record=None,
                           planted_native=None, rare=None,
                           start_year=None, end_year=None,
                           owner_institution_code=None):
    # Build a query for flora occurrences
    query = db_session.query(Occurrence)

    # Join with Species and LocalSpeciesInfo tables
    query = query.join(Species, Occurrence.scientific_name == Species.scientific_name)
    query = query.outerjoin(LocalSpeciesInfo, Occurrence.scientific_name == LocalSpeciesInfo.scientific_name)

    # Filter for occurrences with valid coordinates
    query = query.filter(
        Occurrence.decimal_latitude.isnot(None),
        Occurrence.decimal_longitude.isnot(None)
    )

    # Apply filters if provided
    if species:
        query = query.filter(Occurrence.scientific_name == species)
    if dataset:
        query = query.filter(Occurrence.dataset_name == dataset)

    if reserve:
        # Handle list of reserves or single reserve
        if isinstance(reserve, list) and reserve:
            query = query.filter(Occurrence.reserve_name.in_(reserve))
        elif isinstance(reserve, str) and reserve:
            query = query.filter(Occurrence.reserve_name == reserve)

    if locality:
        query = query.filter(Occurrence.locality.ilike(f'%{locality}%'))
    if habitat:
        query = query.filter(Occurrence.habitat.ilike(f'%{habitat}%'))
    if basis_of_record:
        query = query.filter(Occurrence.basis_of_record.ilike(f'%{basis_of_record}%'))

    # Apply year range filters
    if start_year and end_year:
        query = query.filter(and_(Occurrence.year >= int(start_year), Occurrence.year <= int(end_year)))
    elif start_year:
        query = query.filter(Occurrence.year >= int(start_year))
    elif end_year:
        query = query.filter(Occurrence.year <= int(end_year))

    # Apply 'planted native' filter logic
    if planted_native:
        if planted_native == "Native":
            query = query.filter(Species.exotic == False, LocalSpeciesInfo.planted_native.is_(None))
        elif planted_native == "Exotic":
            query = query.filter(Species.exotic == True)
        elif planted_native == "Planted Native":
            query = query.filter(LocalSpeciesInfo.planted_native == 'Planted Native')
        elif planted_native == "unknown origin":
            query = query.filter(LocalSpeciesInfo.planted_native == 'unknown origin')
        elif planted_native == "not observed":
            query = query.filter(LocalSpeciesInfo.planted_native == 'not observed')

    if rare:
        query = query.filter(Species.threatened_species_status == rare)

    if owner_institution_code:
        query = query.filter(Occurrence.owner_institution_code == owner_institution_code)

    # Order results
    return query.order_by(Occurrence.scientific_name)

def get_observations(db_session, species=None, dataset=None, reserve=None,
                     planted_native=None, rare=None,
                     start_year=None, end_year=None):
    # Retrieve flora observations for map data
    query = db_session.query(Occurrence).filter(
        Occurrence.decimal_latitude.isnot(None),
        Occurrence.decimal_longitude.isnot(None)
    )

    # Join based on filter presence
    if species or planted_native or rare:
        query = query.join(Species, Occurrence.scientific_name == Species.scientific_name)
    if planted_native:
        query = query.outerjoin(LocalSpeciesInfo, Occurrence.scientific_name == LocalSpeciesInfo.scientific_name)

    # Apply filters
    if species:
        query = query.filter(Occurrence.scientific_name == species)
    if dataset:
        query = query.filter(Occurrence.dataset_name == dataset)
    if reserve:
        query = query.filter(Occurrence.reserve_name == reserve)

    # Apply year range filters
    if start_year and end_year:
        query = query.filter(and_(Occurrence.year >= int(start_year), Occurrence.year <= int(end_year)))
    elif start_year:
        query = query.filter(Occurrence.year >= int(start_year))
    elif end_year:
        query = query.filter(Occurrence.year <= int(end_year))

    # Apply 'planted native' filter logic
    if planted_native:
        if planted_native == "Native":
            query = query.filter(Species.exotic == False, LocalSpeciesInfo.planted_native.is_(None))
        elif planted_native == "Exotic":
            query = query.filter(Species.exotic == True)
        elif planted_native == "Planted Native":
            query = query.filter(LocalSpeciesInfo.planted_native == 'Planted Native')
        elif planted_native == "unknown origin":
            query = query.filter(LocalSpeciesInfo.planted_native == 'unknown origin')
        elif planted_native == "not observed":
            query = query.filter(LocalSpeciesInfo.planted_native == 'not observed')

    if rare:
        query = query.filter(Species.threatened_species_status == rare)

    # Convert ORM objects to dictionaries
    return [obs.to_dict() for obs in query.all()]

def get_overall_statistics(db_session):
    # Initialize dictionary for statistics
    stats = {}

    # Flora Statistics
    stats['total_flora_occurrences'] = db_session.query(Occurrence).count()
    stats['distinct_flora_species'] = db_session.query(func.count(distinct(Occurrence.scientific_name))).scalar()
    stats['flora_occurrences_with_coords'] = db_session.query(Occurrence).filter(
        Occurrence.decimal_latitude.isnot(None),
        Occurrence.decimal_longitude.isnot(None)
    ).count()
    stats['distinct_flora_datasets'] = db_session.query(func.count(distinct(Occurrence.dataset_name))).scalar()
    stats['distinct_flora_reserves'] = db_session.query(func.count(distinct(Occurrence.reserve_name))).scalar()

    try:
        # Fauna Statistics (with error handling)
        stats['total_fauna_records'] = db_session.query(Fauna).count()
        stats['distinct_fauna_species'] = db_session.query(func.count(distinct(Fauna.species))).scalar()
        stats['distinct_fauna_genera'] = db_session.query(func.count(distinct(Fauna.genus))).scalar()
        stats['distinct_fauna_families'] = db_session.query(func.count(distinct(Fauna.family))).scalar()
        stats['distinct_fauna_reserves'] = db_session.query(func.count(distinct(Fauna.reserve_name)))\
                                                    .filter(Fauna.reserve_name.isnot(None))\
                                                    .scalar()
    except Exception as e:
        # Print error and set stats to 'N/A'
        print(f"ERROR: Error fetching fauna statistics: {e}", file=sys.stderr)
        stats['total_fauna_records'] = 'N/A'
        stats['distinct_fauna_species'] = 'N/A'
        stats['distinct_fauna_genera'] = 'N/A'
        stats['distinct_fauna_families'] = 'N/A'
        stats['distinct_fauna_reserves'] = 'N/A'

    # Top 5 flora species by occurrence count
    top_species_query = db_session.query(
        Occurrence.scientific_name,
        func.count(Occurrence.scientific_name).label('count')
    ).group_by(Occurrence.scientific_name).order_by(func.count(Occurrence.scientific_name).desc()).limit(5)
    stats['top_5_flora_species'] = top_species_query.all()

    # Flora occurrences by basis of record
    basis_counts = db_session.query(
        Occurrence.basis_of_record,
        func.count(Occurrence.occurrence_id).label('count')
    ).group_by(Occurrence.basis_of_record).all()
    stats['flora_occurrences_by_basis'] = basis_counts

    # Return all statistics
    return stats

# Fauna-related Query Functions

def get_unique_fauna_genera(db_session):
    # Retrieve unique fauna genera names
    unique_genera = db_session.query(Fauna.genus).distinct().all()
    # Return a list, filtering out None values
    return [g.genus for g in unique_genera if g.genus is not None]

def get_unique_fauna_species(db_session):
    # Retrieve unique fauna species names
    unique_species = db_session.query(Fauna.species).distinct().all()
    # Return a list, filtering out None values
    return [s.species for s in unique_species if s.species is not None]

def get_unique_fauna_families(db_session):
    # Retrieve unique fauna families
    unique_families = db_session.query(Fauna.family).distinct().all()
    # Return a list, filtering out None values
    return [f.family for f in unique_families if f.family is not None]

def get_unique_fauna_vernacular_names(db_session):
    # Retrieve unique fauna vernacular names
    unique_vernacular_names = db_session.query(Fauna.vernacular_name).distinct().all()
    # Return a list, filtering out None values
    return [vn.vernacular_name for vn in unique_vernacular_names if vn.vernacular_name is not None]

def get_unique_fauna_class_names(db_session):
    # Retrieve unique fauna class names
    unique_class_names = db_session.query(Fauna.class_name).distinct().all()
    # Return a list, filtering out None values
    return [cn.class_name for cn in unique_class_names if cn.class_name is not None]

def get_unique_fauna_rare_endangered_statuses(db_session):
    # Retrieve unique 'rare_endangered' boolean values for fauna
    unique_rare_endangered = db_session.query(Fauna.rare_endangered).distinct().all()
    # Return a list, filtering out None values
    return [re.rare_endangered for re in unique_rare_endangered if re.rare_endangered is not None]

def get_unique_fauna_local_rare_endangered_statuses(db_session):
    # Retrieve unique 'local_rare_endangered' boolean values for fauna
    unique_local_rare_endangered = db_session.query(Fauna.local_rare_endangered).distinct().all()
    # Return a list, filtering out None values
    return [lre.local_rare_endangered for lre in unique_local_rare_endangered if lre.local_rare_endangered is not None]

def get_unique_fauna_exotic_statuses(db_session):
    # Retrieve unique 'exotic' boolean values for fauna
    unique_exotic = db_session.query(Fauna.exotic).distinct().all()
    # Return a list, filtering out None values
    return [e.exotic for e in unique_exotic if e.exotic is not None]

def get_unique_fauna_years(db_session):
    # Retrieve unique years from Fauna data
    years = db_session.query(Fauna.year)\
                             .filter(Fauna.year.isnot(None))\
                             .distinct()\
                             .order_by(Fauna.year.desc())\
                             .all()
    # Return a list, filtering out None values
    return [y.year for y in years if y.year is not None]

def get_unique_fauna_reserve_names(db_session):
    # Retrieve unique reserve names for fauna
    unique_reserves = db_session.query(Fauna.reserve_name).distinct().all()
    # Return a list, filtering out None values
    return [r.reserve_name for r in unique_reserves if r.reserve_name is not None]

def get_options_fauna(db_session):
    # Aggregate all filter options for fauna records
    # Convert boolean options to strings for frontend
    rare_endangered_options_str = [str(b) for b in get_unique_fauna_rare_endangered_statuses(db_session)]
    local_rare_endangered_options_str = [str(b) for b in get_unique_fauna_local_rare_endangered_statuses(db_session)]
    exotic_options_str = [str(b) for b in get_unique_fauna_exotic_statuses(db_session)]

    return {
        "genusOptions": sorted(get_unique_fauna_genera(db_session)),
        "speciesOptions": sorted(get_unique_fauna_species(db_session)),
        "familyOptions": sorted(get_unique_fauna_families(db_session)),
        "vernacularNameOptions": sorted(get_unique_fauna_vernacular_names(db_session)),
        "classNameOptions": sorted(get_unique_fauna_class_names(db_session)),
        "rareEndangeredOptions": sorted(rare_endangered_options_str),
        "localRareEndangeredOptions": sorted(local_rare_endangered_options_str),
        "exoticOptions": sorted(exotic_options_str),
        "yearOptions": sorted(get_unique_fauna_years(db_session)),
        "reserveNameOptions": sorted(get_unique_fauna_reserve_names(db_session)),
    }

def get_fauna_query(db_session, genus=None, species=None, family=None, vernacular_name=None,
                      class_name=None, rare_endangered=None,
                      local_rare_endangered=None, exotic=None, year=None, reserve_name=None):
    # Build a query for fauna records
    query = db_session.query(Fauna)

    # Apply filters if provided
    if genus:
        query = query.filter(Fauna.genus.ilike(f'%{genus}%'))
    if species:
        query = query.filter(Fauna.species.ilike(f'%{species}%'))
    if family:
        query = query.filter(Fauna.family.ilike(f'%{family}%'))
    if vernacular_name:
        query = query.filter(Fauna.vernacular_name.ilike(f'%{vernacular_name}%'))
    if class_name:
        query = query.filter(Fauna.class_name.ilike(f'%{class_name}%'))

    # Convert string boolean to actual boolean for filtering
    if rare_endangered is not None:
        bool_rare_endangered = str(rare_endangered).lower() == 'true'
        query = query.filter(Fauna.rare_endangered == bool_rare_endangered)

    if local_rare_endangered is not None:
        bool_local_rare_endangered = str(local_rare_endangered).lower() == 'true'
        query = query.filter(Fauna.local_rare_endangered == bool_local_rare_endangered)

    if exotic is not None:
        bool_exotic = str(exotic).lower() == 'true'
        query = query.filter(Fauna.exotic == bool_exotic)

    if year:
        try:
            query = query.filter(Fauna.year == int(year))
        except ValueError:
            query = query.filter(cast(Fauna.year, String).ilike(f'%{year}%'))

    if reserve_name:
        # Handle list of reserves or single reserve
        if isinstance(reserve_name, list) and reserve_name:
            non_empty_reserves = [r.strip() for r in reserve_name if r.strip()]
            if non_empty_reserves:
                query = query.filter(Fauna.reserve_name.in_(non_empty_reserves))
        elif isinstance(reserve_name, str) and reserve_name.strip():
            query = query.filter(Fauna.reserve_name == reserve_name)

    # Order results
    return query.order_by(Fauna.species)

def get_flora_all_species_report(db_session):
    # Fetch detailed flora species data for "All Species" report
    results = db_session.query(
        Species.scientific_name.label('species_name'),
        func.count(Occurrence.occurrence_id).label('occurrence_count'),
        func.sum(func.coalesce(Occurrence.individual_count, 1)).label('total_individual_count'),
        Species.exotic.label('exotic'),
        LocalSpeciesInfo.planted_native.label('planted_native')
    ).outerjoin(Occurrence, Species.scientific_name == Occurrence.scientific_name) \
     .outerjoin(LocalSpeciesInfo, Species.scientific_name == LocalSpeciesInfo.scientific_name) \
     .group_by(
        Species.scientific_name,
        Species.exotic,
        LocalSpeciesInfo.planted_native
    ).order_by(Species.scientific_name).all()

    # Convert rows to dictionaries
    return [row._asdict() for row in results]

def get_fauna_all_species_report(db_session):
    # Fetch all fauna species data for "All Species" report
    fauna_list = db_session.query(
        Fauna.genus.label('genus'),
        Fauna.species.label('species'),
        Fauna.vernacular_name.label('vernacular_name'),
        Fauna.family.label('family'),
        Fauna.class_name.label('class_name'),
        Fauna.exotic.label('exotic'),
        Fauna.rare_endangered.label('rare_endangered'),
        Fauna.local_rare_endangered.label('local_rare_endangered'),
        Fauna.year.label('year'),
        Fauna.decimal_longitude.label('decimal_longitude'),
        Fauna.decimal_latitude.label('decimal_latitude'),
        Fauna.reserve_name.label('reserve_name')
    ).order_by(Fauna.genus, Fauna.species).all()

    formatted_fauna = []
    for f in fauna_list:
        # Format boolean fields as 'Yes'/'No' and handle None values
        formatted_fauna.append({
            'Genus': f.genus if f.genus is not None else 'N/A',
            'Species': f.species if f.species is not None else 'N/A',
            'Vernacular Name': f.vernacular_name if f.vernacular_name is not None else 'N/A',
            'Family': f.family if f.family is not None else 'N/A',
            'Class Name': f.class_name if f.class_name is not None else 'N/A',
            'Exotic': 'Yes' if f.exotic else 'No',
            'Rare/Endangered': 'Yes' if f.rare_endangered else 'No',
            'Local Rare/Endangered': 'Yes' if f.local_rare_endangered else 'No',
            'Year': f.year,
            'Decimal Longitude': f.decimal_longitude,
            'Decimal Latitude': f.decimal_latitude,
            'Reserve Name': f.reserve_name
        })
    return formatted_fauna

def get_summary_report(db_session, report_type):
    # Generate a summary report based on report type (Flora or Fauna)
    if report_type == "Flora":
        summary_query = db_session.query(
            DataSource.data_source_name.label('source_file'),
            Reserve.reserve_name.label('location_name'),
            func.count(distinct(Occurrence.scientific_name)).label('total_species'),
            func.count(distinct(case((Species.exotic == True, Occurrence.scientific_name)))).label('num_exotic_species'),
            func.count(distinct(case((Species.threatened_species_status.isnot(None), Occurrence.scientific_name)))).label('num_listed_re'),
            func.count(distinct(case((LocalSpeciesInfo.planted_native == 'Planted Native', LocalSpeciesInfo.scientific_name)))).label('num_planted_native')
        ).outerjoin(Occurrence, Occurrence.dataset_name == DataSource.data_source_name) \
         .outerjoin(Reserve, Occurrence.reserve_name == Reserve.reserve_name) \
         .outerjoin(Species, Occurrence.scientific_name == Species.scientific_name) \
         .outerjoin(LocalSpeciesInfo, Occurrence.scientific_name == LocalSpeciesInfo.scientific_name) \
         .group_by(DataSource.data_source_name, Reserve.reserve_name) \
         .order_by(DataSource.data_source_name, Reserve.reserve_name) \
         .all()

        formatted_summary = []
        for row in summary_query:
            formatted_summary.append({
                'Source File': row.source_file,
                'Location Name': row.location_name,
                'Total Species': row.total_species,
                'Number of Exotic Species': row.num_exotic_species,
                'Number of Listed R&E': row.num_listed_re,
                'Number of Planted Native': row.num_planted_native
            })
        return formatted_summary
    elif report_type == "Fauna":
        summary_query = db_session.query(
            Fauna.class_name.label('class_name'),
            Fauna.reserve_name.label('reserve_name'),
            func.count(distinct(Fauna.species)).label('total_species'),
            func.count(distinct(case((Fauna.exotic == True, Fauna.species)))).label('num_exotic_species'),
            func.count(distinct(case((Fauna.rare_endangered == True, Fauna.species)))).label('num_rare_endangered_species'),
            func.count(distinct(case((Fauna.local_rare_endangered == True, Fauna.species)))).label('num_local_rare_endangered_species')
        ).group_by(Fauna.class_name, Fauna.reserve_name).order_by(Fauna.class_name, Fauna.reserve_name).all()

        formatted_fauna_summary = []
        for row in summary_query:
            formatted_fauna_summary.append({
                'Class Name': row.class_name if row.class_name is not None else 'Unknown',
                'Reserve Name': row.reserve_name if row.reserve_name is not None else 'Unknown',
                'Total Species': row.total_species,
                'Number of Exotic Species': row.num_exotic_species,
                'Number of Rare/Endangered Species': row.num_rare_endangered_species,
                'Number of Local Rare/Endangered Species': row.num_local_rare_endangered_species,
            })
        return formatted_fauna_summary
    return []

def get_flora_report_by_reserve(db_session):
    # Generate a report for Flora showing occurrences and distinct species per reserve
    report_data = db_session.query(
        Reserve.reserve_name.label('reserve_name'),
        func.count(Occurrence.occurrence_id).label('num_occurrences'),
        func.count(distinct(Occurrence.scientific_name)).label('num_distinct_species')
    ).join(Occurrence, Reserve.reserve_name == Occurrence.reserve_name) \
     .group_by(Reserve.reserve_name) \
     .order_by(Reserve.reserve_name) \
     .all()

    formatted_report = []
    for row in report_data:
        formatted_report.append({
            'Reserve Name': row.reserve_name,
            'Number of Occurrences': row.num_occurrences,
            'Number of Distinct Species': row.num_distinct_species
        })
    return formatted_report